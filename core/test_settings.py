import os
import runpy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase
from dotenv import load_dotenv


class EnvironmentSettingsTests(SimpleTestCase):
    def test_local_file_loads_before_settings_are_read(self) -> None:
        project = Path(__file__).resolve().parent.parent
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                'DJANGO_SECRET_KEY="local-test-key"\n'
                'DJANGO_DEBUG=True\n'
                'DJANGO_ALLOWED_HOSTS=127.0.0.1\n'
                'GOOGLE_CLIENT_ID=local-test-client\n'
                'GOOGLE_CLIENT_SECRET="local-test-secret"\n',
                encoding="utf-8-sig",
            )
            with patch.dict(os.environ, {}, clear=True):
                with patch("dotenv.load_dotenv") as loader:
                    loader.side_effect = lambda path, **options: load_dotenv(
                        env_file, **options,
                    )
                    settings = runpy.run_path(str(project / "config/settings.py"))
                    loader.assert_called_once_with(
                        project / ".env", override=False, encoding="utf-8-sig",
                    )
                self.assertEqual(settings["SECRET_KEY"], "local-test-key")
                self.assertTrue(settings["DEBUG"])
                self.assertEqual(settings["ALLOWED_HOSTS"], ["127.0.0.1"])
                self.assertTrue(settings["GOOGLE_CONFIGURED"])
                self.assertEqual(settings["GOOGLE_CLIENT_SECRET"], "local-test-secret")

    def test_existing_environment_takes_precedence_including_empty_values(self) -> None:
        project = Path(__file__).resolve().parent.parent
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                'DJANGO_SECRET_KEY=file-test-key\n'
                'DJANGO_DEBUG=True\n'
                'GOOGLE_CLIENT_ID=file-test-client\n'
                'GOOGLE_CLIENT_SECRET=file-test-secret\n',
                encoding="utf-8",
            )
            environment = {
                "DJANGO_SECRET_KEY": "environment-test-key",
                "DJANGO_DEBUG": "False",
                "GOOGLE_CLIENT_ID": "environment-test-client",
                "GOOGLE_CLIENT_SECRET": "",
            }
            with patch.dict(os.environ, environment, clear=True):
                with patch("dotenv.load_dotenv") as loader:
                    loader.side_effect = lambda path, **options: load_dotenv(
                        env_file, **options,
                    )
                    settings = runpy.run_path(str(project / "config/settings.py"))
                self.assertEqual(settings["SECRET_KEY"], "environment-test-key")
                self.assertFalse(settings["DEBUG"])
                self.assertEqual(settings["GOOGLE_CLIENT_ID"], "environment-test-client")
                self.assertEqual(settings["GOOGLE_CLIENT_SECRET"], "")
                self.assertFalse(settings["GOOGLE_CONFIGURED"])
