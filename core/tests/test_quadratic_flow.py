"""Testes de fluxo HTTP para o módulo quadrático — espelha test_equations.py."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Exercise
from core.views import save_exercise_state

# Equação fixada para os testes: x² − 5x + 6 = 0
# a=1, b=-5, c=6, Δ=1, x₁=2, x₂=3
_A, _B, _C, _DELTA = 1, -5, 6, 1


def _make(user, *, a=_A, b=_B, c=_C, **kwargs):
    return Exercise.objects.create(
        user=user, kind=Exercise.Kind.QUADRATIC,
        a=a, b=b, c=c, creation_key=uuid4(), **kwargs,
    )


class QuadraticFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="quad")
        self.other = get_user_model().objects.create_user(username="other_quad")
        self.client.force_login(self.user)
        self.exercise = _make(self.user)

    def _post(self, **fields):
        self.exercise.refresh_from_db()
        return self.client.post(
            reverse("answer_exercise", args=[self.exercise.pk]),
            {"revision": self.exercise.revision, **fields},
        )

    # ------------------------------------------------------------------
    # Fluxo feliz: dois passos corretos na primeira tentativa
    # ------------------------------------------------------------------

    def test_step1_shows_hint_not_answer(self):
        response = self.client.get(reverse("exercise", args=[self.exercise.pk]))
        self.assertContains(response, "Calcule o discriminante")
        self.assertNotContains(response, f"Δ = {_DELTA}")  # não entrega o valor de Δ antes

    def test_correct_two_steps_first_try(self):
        # Passo 1: Δ correto
        self._post(first=str(_DELTA))
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 2)

        # Passo 2: raízes corretas (ordem não importa)
        self._post(first="3", second="2")
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 3)
        self.assertIsNotNone(self.exercise.completed_at)
        self.assertTrue(self.exercise.first_try)

    def test_wrong_delta_stays_on_step1(self):
        self._post(first="999")
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 1)
        self.assertEqual(len(self.exercise.attempts), 1)
        self.assertFalse(self.exercise.attempts[0]["correct"])

    def test_wrong_sign_delta_hint(self):
        # Erro clássico: b² + 4ac em vez de b² − 4ac
        wrong = _B * _B + 4 * _A * _C
        self._post(first=str(wrong))
        response = self.client.get(reverse("exercise", args=[self.exercise.pk]))
        self.assertContains(response, "sinal")

    def test_wrong_roots_step2(self):
        self._post(first=str(_DELTA))               # passo 1 correto
        self._post(first="0", second="0")           # passo 2 errado
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 2)
        self.assertIsNone(self.exercise.completed_at)

    def test_completed_shows_solution(self):
        self._post(first=str(_DELTA))
        self._post(first="2", second="3")
        response = self.client.get(reverse("exercise", args=[self.exercise.pk]))
        self.assertContains(response, "Equação resolvida!")
        self.assertContains(response, "✓")

    # ------------------------------------------------------------------
    # Consulta à solução
    # ------------------------------------------------------------------

    def test_solution_view_closes_without_credit(self):
        self.exercise.refresh_from_db()
        self.client.post(
            reverse("view_solution", args=[self.exercise.pk]),
            {"revision": self.exercise.revision},
        )
        self.exercise.refresh_from_db()
        self.assertTrue(self.exercise.solution_viewed)
        self.assertFalse(self.exercise.first_try)
        self.assertEqual(self.exercise.step, 3)

    # ------------------------------------------------------------------
    # Geração e isolamento entre usuários
    # ------------------------------------------------------------------

    @patch("core.views.quadratic.generate_parameters", return_value=(_A, _B, _C, _DELTA))
    def test_generation_belongs_to_logged_user(self, _gen):
        creation_key = uuid4()
        self.client.post(reverse("generate_exercise"), {
            "kind": "quadratic", "creation_key": creation_key,
            "user_id": self.other.pk,  # tentativa de injetar outro user
        })
        ex = Exercise.objects.get(creation_key=creation_key)
        self.assertEqual(ex.user, self.user)
        self.assertEqual((ex.a, ex.b, ex.c), (_A, _B, _C))

    def test_other_user_gets_404(self):
        self.client.force_login(self.other)
        answer_url = reverse("answer_exercise", args=[self.exercise.pk])
        detail_url = reverse("exercise", args=[self.exercise.pk])
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.assertEqual(
            self.client.post(answer_url, {"revision": 0, "first": 1, "second": 1}).status_code,
            404,
        )

    def test_quadratic_exercises_isolated_from_linear(self):
        linear = Exercise.objects.create(
            user=self.user, kind=Exercise.Kind.LINEAR,
            a=2, b=3, c=7, creation_key=uuid4(),
        )
        quad_filter = self.client.get(reverse("student"), {"module": "quadratic"})
        linear_filter = self.client.get(reverse("student"), {"module": "equations"})
        quad_ids = [e.pk for e in quad_filter.context["recent_exercises"]]
        lin_ids = [e.pk for e in linear_filter.context["recent_exercises"]]
        self.assertIn(self.exercise.pk, quad_ids)
        self.assertNotIn(linear.pk, quad_ids)
        self.assertIn(linear.pk, lin_ids)
        self.assertNotIn(self.exercise.pk, lin_ids)

    # ------------------------------------------------------------------
    # Autenticação e CSRF
    # ------------------------------------------------------------------

    def test_authentication_required(self):
        anon = Client()
        self.assertEqual(anon.get(reverse("quadratic_content")).status_code, 302)
        self.assertEqual(self.client.get(reverse("quadratic_content")).status_code, 200)

    def test_csrf_required(self):
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        for name in ("answer_exercise", "view_solution"):
            url = reverse(name, args=[self.exercise.pk])
            self.assertEqual(protected.post(url, {"revision": 0, "first": 1}).status_code, 403)

    # ------------------------------------------------------------------
    # Progresso no painel do aluno
    # ------------------------------------------------------------------

    def test_progress_counts_quadratic_separately(self):
        # Completa a quadrática
        self._post(first=str(_DELTA))
        self._post(first="2", second="3")
        # Filtra por módulo
        quad = self.client.get(reverse("student"), {"module": "quadratic"})
        self.assertEqual(quad.context["completed_count"], 1)
        self.assertEqual(quad.context["first_try_count"], 1)
        self.assertEqual(quad.context["first_try_percent"], 100.0)


class QuadraticConcurrencyTests(TransactionTestCase):
    """Apenas um envio simultâneo deve concluir o exercício."""

    def test_only_one_simultaneous_completion_wins(self):
        user = get_user_model().objects.create_user(username="quad-concurrent")
        exercise = _make(
            user, step=2,
            attempts=[{"step": 1, "answers": {"first": str(_DELTA)}, "correct": True}],
        )
        barrier = Barrier(2)

        def submit():
            close_old_connections()
            snapshot = Exercise.objects.get(pk=exercise.pk)
            barrier.wait(timeout=10)
            try:
                return save_exercise_state(
                    snapshot, step=3, completed_at=timezone.now(),
                    attempts=snapshot.attempts + [{
                        "step": 2, "answers": {"first": "2", "second": "3"}, "correct": True,
                    }],
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))

        self.assertEqual(sorted(results), [False, True])
        exercise.refresh_from_db()
        self.assertEqual(exercise.revision, 1)
        self.assertEqual(len(exercise.attempts), 2)
        self.assertTrue(exercise.first_try)
