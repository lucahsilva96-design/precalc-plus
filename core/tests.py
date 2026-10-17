from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from requests.exceptions import ConnectionError

from allauth.socialaccount.models import SocialAccount, SocialToken

PROVIDERS = {"google": {
    "SCOPE": ["profile", "email"],
    "OAUTH_PKCE_ENABLED": True,
    "APP": {"client_id": "test-client", "secret": "test-secret", "key": ""},
}}


class PagesTests(TestCase):
    @override_settings(GOOGLE_CONFIGURED=False)
    def test_public_pages_and_pending_configuration(self) -> None:
        self.assertContains(self.client.get("/"), "Fatoração")
        self.assertContains(self.client.get("/accounts/login/"), "configuração pendente")
        for path in ("/accounts/google/login/", "/accounts/google/login/callback/"):
            self.assertEqual(self.client.get(path).status_code, 503)

    def test_private_area_and_logout(self) -> None:
        self.assertRedirects(self.client.get("/aluno/"), "/accounts/login/?next=/aluno/")
        user = get_user_model().objects.create_user(username="ana", first_name="Ana")
        self.client.force_login(user)
        response = self.client.get("/aluno/")
        self.assertContains(response, "Olá, Ana!")
        self.assertContains(response, "Você ainda não realizou exercícios")
        self.client.get("/accounts/logout/")
        self.assertIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.post("/accounts/logout/"), "/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get("/aluno/").status_code, 302)

    def test_csrf_required(self) -> None:
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/accounts/google/login/").status_code, 403)
        self.assertEqual(client.post("/accounts/logout/").status_code, 403)


@override_settings(GOOGLE_CONFIGURED=True, SOCIALACCOUNT_PROVIDERS=PROVIDERS)
class GoogleTests(TestCase):
    def start_login(self, next_url: str = "/aluno/") -> str:
        response = self.client.post("/accounts/google/login/", {"next": next_url})
        self.assertEqual(response.status_code, 302)
        target = urlparse(response.url)
        self.assertEqual(target.netloc, "accounts.google.com")
        query = parse_qs(target.query)
        self.assertIn("code_challenge", query)
        return query["state"][0]

    def test_get_does_not_start_oauth(self) -> None:
        self.assertContains(self.client.get("/accounts/google/login/"), "Entrar com Google")

    def test_cancel_failure_and_invalid_state(self) -> None:
        state = self.start_login()
        response = self.client.get("/accounts/google/login/callback/", {
            "state": state, "error": "access_denied",
        }, follow=True)
        self.assertContains(response, "Login cancelado")
        state = self.start_login()
        response = self.client.get("/accounts/google/login/callback/", {
            "state": state, "error": "server_error",
        })
        self.assertContains(response, "Não foi possível entrar", status_code=401)
        response = self.client.get("/accounts/google/login/callback/", {
            "state": "invalid", "code": "invalid",
        })
        self.assertContains(response, "Não foi possível entrar", status_code=401)
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch("allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token")
    def test_network_failure(self, token_mock) -> None:
        token_mock.side_effect = ConnectionError("simulated outage")
        state = self.start_login()
        response = self.client.get("/accounts/google/login/callback/", {
            "state": state, "code": "test-code",
        })
        self.assertContains(response, "Não foi possível entrar", status_code=401)
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch("allauth.socialaccount.providers.google.views.GoogleOAuth2Adapter._fetch_user_info")
    @patch("allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token")
    def test_creation_reuse_tokens_and_safe_redirect(self, token_mock, identity_mock) -> None:
        token_mock.return_value = {"access_token": "mock-token", "expires_in": 3600}
        identity_mock.return_value = {
            "id": "google-123", "email": "ana@example.com", "verified_email": True,
            "given_name": "Ana", "family_name": "Silva", "name": "Ana Silva",
        }
        for _ in range(2):
            state = self.start_login("https://untrusted.example/")
            response = self.client.get("/accounts/google/login/callback/", {
                "state": state, "code": "test-code",
            })
            self.assertRedirects(response, "/aluno/")
            self.assertEqual(get_user_model().objects.count(), 1)
            self.assertEqual(SocialAccount.objects.get().uid, "google-123")
            self.assertEqual(SocialToken.objects.count(), 0)
            self.client.post("/accounts/logout/")

    @patch("allauth.socialaccount.providers.google.views.GoogleOAuth2Adapter._fetch_user_info")
    @patch("allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token")
    def test_email_collision_does_not_link_existing_user(self, token_mock, identity_mock) -> None:
        get_user_model().objects.create_user(username="existing", email="ana@example.com")
        token_mock.return_value = {"access_token": "mock-token"}
        identity_mock.return_value = {
            "id": "different-google-id", "email": "ana@example.com", "verified_email": True,
        }
        state = self.start_login()
        self.client.get("/accounts/google/login/callback/", {"state": state, "code": "test"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(SocialAccount.objects.exists())
