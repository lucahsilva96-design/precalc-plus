from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.http import HttpResponse
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from . import equations
from .forms import AnswerForm
from .models import Exercise
from .views import save_exercise_state


class EquationMathTests(SimpleTestCase):
    def test_generation_and_correction_across_all_limits(self) -> None:
        for a in range(-5, 6):
            if a == 0:
                continue
            for b in range(-10, 11):
                for x in range(-9, 10):
                    with patch("core.equations.choice", return_value=a):
                        with patch("core.equations.randint", side_effect=[b, x]):
                            parameters = equations.generate_parameters()
                    self.assertEqual(parameters, (a, b, a * x + b))
                    c = parameters[2]
                    self.assertLessEqual(abs(c), 55)
                    self.assertTrue(equations.check_answer(a, b, c, 1, c - b)[0])
                    self.assertTrue(equations.check_answer(a, b, c, 2, x)[0])

    def test_formatting_feedback_and_complete_example(self) -> None:
        for parameters, text in (
            ((1, -3, 2), "x − 3 = 2"),
            ((-1, 0, -4), "−x = −4"),
            ((-3, 6, 0), "−3x + 6 = 0"),
            ((3, 0, 0), "3x = 0"),
        ):
            self.assertEqual(equations.expression(*parameters), text)
        self.assertIn("c + b", equations.check_answer(3, 6, 18, 1, 24)[1])
        self.assertIn("c + b", equations.check_answer(-2, -3, 5, 1, 2)[1])
        self.assertIn("sinal oposto", equations.check_answer(-2, -3, 5, 2, 4)[1])
        self.assertIn("Confira", equations.check_answer(3, 6, 18, 1, 9)[1])
        result, explanation, verification = equations.solution(3, 6, 18)
        self.assertEqual(result, "3x = 12; x = 4")
        self.assertIn("Subtraia 6 dos dois lados", explanation)
        self.assertIn("(3) × (4) + (6) = 18", verification)

    def test_invalid_fields_and_zero(self) -> None:
        for step, values in (
            (1, ("", "abc", "1.5", "46", "-46", "1" * 5000)),
            (2, ("", "x=4", "10", "-10")),
        ):
            for value in values:
                form = AnswerForm(
                    {"revision": 0, "first": value}, kind="linear", step=step,
                )
                self.assertFalse(form.is_valid())
                self.assertIn("id_first_error", form.as_div())
        for step in (1, 2):
            form = AnswerForm(
                {"revision": 0, "first": "0"}, kind="linear", step=step,
            )
            self.assertTrue(form.is_valid())


class EquationFlowTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username="equation")
        self.other = get_user_model().objects.create_user(username="other")
        self.client.force_login(self.user)
        self.exercise = Exercise.objects.create(
            user=self.user, kind="linear", a=3, b=6, c=18,
            creation_key=uuid4(),
        )

    def submit(self, value: object) -> HttpResponse:
        self.exercise.refresh_from_db()
        return self.client.post(reverse("answer_exercise", args=[self.exercise.pk]), {
            "revision": self.exercise.revision, "first": value,
        })

    def test_two_steps_wrong_retry_and_no_future_answer(self) -> None:
        url = reverse("exercise", args=[self.exercise.pk])
        response = self.client.get(url)
        self.assertContains(response, "Subtraia 6 dos dois lados")
        self.assertNotContains(response, "x = 4")
        self.assertNotContains(response, "3x = 12")
        self.submit(24)
        response = self.client.get(url)
        self.assertContains(response, "c + b")
        self.assertContains(response, 'value="24"')
        self.submit(12)
        response = self.client.get(url)
        self.assertContains(response, "3x = 12")
        self.assertNotContains(response, "x = 4")
        self.submit(4)
        response = self.client.get(url)
        self.assertContains(response, "Equação resolvida!")
        self.assertContains(response, "(3) × (4) + (6) = 18")
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 3)
        self.assertFalse(self.exercise.first_try)
        self.assertEqual(len(self.exercise.attempts), 3)

    def test_negative_and_zero_solutions(self) -> None:
        for a, b, x in ((-1, -3, -5), (2, 0, 0), (-3, 0, 4), (1, 3, -2)):
            self.exercise = Exercise.objects.create(
                user=self.user, kind="linear", a=a, b=b, c=a * x + b,
                creation_key=uuid4(),
            )
            self.submit(a * x)
            self.submit(x)
            self.exercise.refresh_from_db()
            self.assertTrue(self.exercise.first_try)

    def test_invalid_attempt_consultation_and_closed_state(self) -> None:
        self.submit("abc")
        response = self.client.get(reverse("exercise", args=[self.exercise.pk]))
        self.assertContains(response, 'value="abc"')
        self.assertContains(response, "Informe um número inteiro")
        self.exercise.refresh_from_db()
        url = reverse("view_solution", args=[self.exercise.pk])
        data = {"revision": self.exercise.revision}
        self.client.post(url, data)
        self.client.post(url, data)
        self.submit(12)
        self.exercise.refresh_from_db()
        self.assertTrue(self.exercise.solution_viewed)
        self.assertFalse(self.exercise.first_try)
        self.assertEqual(len(self.exercise.attempts), 1)

    @patch("core.views.equations.generate_parameters", return_value=(-2, 3, -5))
    def test_generation_owner_and_replay(self, generator) -> None:
        data = {
            "kind": "linear", "creation_key": uuid4(),
            "user_id": self.other.pk, "a": 0, "answer": 999,
        }
        first = self.client.post(reverse("generate_exercise"), data)
        second = self.client.post(reverse("generate_exercise"), data)
        self.assertEqual(first.url, second.url)
        generated = Exercise.objects.get(creation_key=data["creation_key"])
        self.assertEqual(generated.user, self.user)
        self.assertEqual((generated.a, generated.b, generated.c), (-2, 3, -5))
        self.assertEqual(Exercise.objects.count(), 2)

    def test_replay_out_of_order_and_foreign_access(self) -> None:
        answer_url = reverse("answer_exercise", args=[self.exercise.pk])
        self.client.post(answer_url, {"revision": 99, "first": 4, "step": 2})
        self.client.post(answer_url, {"revision": 0, "first": 4, "step": 2})
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 1)
        data = {"revision": self.exercise.revision, "first": 12}
        self.client.post(answer_url, data)
        self.client.post(answer_url, data)
        self.exercise.refresh_from_db()
        self.assertEqual(len(self.exercise.attempts), 2)
        self.assertEqual(self.exercise.step, 2)
        self.client.force_login(self.other)
        for name in ("exercise", "answer_exercise", "view_solution"):
            url = reverse(name, args=[self.exercise.pk])
            response = (
                self.client.get(url) if name == "exercise"
                else self.client.post(url, data)
            )
            self.assertEqual(response.status_code, 404)
        self.assertNotContains(self.client.get(reverse("student")), "3x + 6 = 18")

    def test_authentication_and_csrf(self) -> None:
        anonymous = Client()
        self.assertEqual(anonymous.get(reverse("equations_content")).status_code, 302)
        self.assertEqual(self.client.get(reverse("equations_content")).status_code, 200)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        for name in ("answer_exercise", "view_solution"):
            url = reverse(name, args=[self.exercise.pk])
            self.assertEqual(anonymous.post(url).status_code, 302)
            self.assertEqual(protected.post(url, {"revision": 0}).status_code, 403)
            self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(protected.post(reverse("generate_exercise")).status_code, 403)

    def test_progress_filters_totals_and_empty_state(self) -> None:
        self.submit(12)
        self.submit(4)
        for _ in range(3):
            Exercise.objects.create(
                user=self.user, kind="common", a=6, b=9, step=3,
                completed_at=timezone.now(), creation_key=uuid4(),
                solution_viewed=True,
            )
        Exercise.objects.create(
            user=self.other, kind="linear", a=1, b=0, c=4,
            creation_key=uuid4(),
        )
        response = self.client.get(reverse("student"))
        self.assertEqual(response.context["completed_count"], 4)
        self.assertEqual(response.context["first_try_count"], 1)
        self.assertEqual(response.context["first_try_percent"], 25)
        factoring = self.client.get(reverse("student"), {"module": "factoring"})
        self.assertEqual(factoring.context["completed_count"], 3)
        self.assertEqual(factoring.context["first_try_percent"], 0)
        linear = self.client.get(reverse("student"), {"module": "equations"})
        self.assertEqual(linear.context["completed_count"], 1)
        self.assertEqual(linear.context["first_try_percent"], 100)
        self.assertEqual(len(linear.context["recent_exercises"]), 1)
        self.client.force_login(self.other)
        empty = self.client.get(reverse("student"), {"module": "factoring"})
        self.assertIsNone(empty.context["first_try_percent"])
        self.assertFalse(empty.context["has_exercises"])


class EquationMigrationTests(TransactionTestCase):
    def test_old_factoring_record_keeps_parameters_attempts_and_meaning(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate([("core", "0001_initial")])
        apps = executor.loader.project_state([("core", "0001_initial")]).apps
        user = get_user_model().objects.create_user(username="migration")
        attempts = [
            {"step": 1, "answers": {"first": "3"}, "correct": True},
            {"step": 2, "answers": {"first": "2", "second": "3"}, "correct": True},
        ]
        old = apps.get_model("core", "Exercise").objects.create(
            user_id=user.pk, kind="common", a=6, b=9, step=3,
            attempts=attempts, creation_key=uuid4(), completed_at=timezone.now(),
        )
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("core", "0002_linear_equations")])
            exercise = Exercise.objects.get(pk=old.pk)
            self.assertEqual((exercise.a, exercise.b, exercise.c), (6, 9, None))
            self.assertEqual(exercise.attempts, attempts)
            self.assertEqual(exercise.created_at, old.created_at)
            self.assertEqual(exercise.completed_at, old.completed_at)
            self.assertTrue(exercise.first_try)
        finally:
            MigrationExecutor(connection).migrate([("core", "0002_linear_equations")])

    def test_only_one_simultaneous_linear_completion_wins(self) -> None:
        user = get_user_model().objects.create_user(username="concurrent-linear")
        exercise = Exercise.objects.create(
            user=user, kind="linear", a=-2, b=3, c=-5, step=2,
            creation_key=uuid4(),
            attempts=[{"step": 1, "answers": {"first": "-8"}, "correct": True}],
        )
        barrier = Barrier(2)

        def submit() -> bool:
            close_old_connections()
            snapshot = Exercise.objects.get(pk=exercise.pk)
            barrier.wait(timeout=10)
            try:
                return save_exercise_state(
                    snapshot, step=3, completed_at=timezone.now(),
                    attempts=snapshot.attempts + [{
                        "step": 2, "answers": {"first": "4"}, "correct": True,
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
