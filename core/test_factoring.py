from concurrent.futures import ThreadPoolExecutor
from math import gcd
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .factoring import check_answer, generate_parameters, solution
from .forms import AnswerForm, GenerationForm
from .models import Exercise
from .views import save_exercise_state


class MathTests(SimpleTestCase):
    def test_generation_at_every_random_choice(self) -> None:
        for factor in range(2, 6):
            for left in range(1, 7):
                for right in range(1, 7):
                    with patch("core.factoring.randint", side_effect=[factor, left, right]):
                        a, b = generate_parameters("common")
                    self.assertTrue(1 <= a <= 30 and 1 <= b <= 30)
                    self.assertGreater(gcd(a, b), 1)
                    divisor = gcd(a, b)
                    self.assertTrue(check_answer("common", a, b, 1, {"first": divisor})[0])
                    self.assertTrue(check_answer(
                        "common", a, b, 2,
                        {"first": a // divisor, "second": b // divisor},
                    )[0])
        for root in range(2, 10):
            with patch("core.factoring.randint", return_value=root):
                self.assertEqual(generate_parameters("squares"), (1, root * root))
            self.assertTrue(check_answer("squares", 1, root * root, 1, {"first": root})[0])
            for numbers in ((-root, root), (root, -root)):
                self.assertTrue(check_answer(
                    "squares", 1, root * root, 2,
                    {"first": numbers[0], "second": numbers[1]},
                )[0])
        with self.assertRaises(ValueError):
            generate_parameters("unsupported")

    def test_math_feedback_and_solutions(self) -> None:
        examples = (
            ("common", 6, 9, 1, {"first": 2}, "um dos coeficientes"),
            ("common", 12, 18, 1, {"first": 3}, "divisor comum maior"),
            ("common", 6, 9, 1, {"first": 5}, "sem deixar resto"),
            ("common", 6, 9, 2, {"first": 3, "second": 2}, "divisão"),
            ("squares", 1, 9, 1, {"first": 2}, "resulta em 9"),
            ("squares", 1, 9, 2, {"first": 3, "second": 3}, "sinais opostos"),
        )
        for kind, a, b, step, answers, hint in examples:
            correct, feedback = check_answer(kind, a, b, step, answers)
            self.assertFalse(correct)
            self.assertIn(hint, feedback)
        self.assertEqual(solution("common", 6, 9)[0], "3(2x + 3)")
        self.assertEqual(solution("squares", 1, 9)[0], "(x − 3)(x + 3)")

    def test_forms_reject_invalid_numbers_and_lengths(self) -> None:
        for value in ("", "abc", "1.5", "-1", "0", "31", "1" * 5000):
            form = AnswerForm({"revision": 0, "first": value}, kind="common", step=1)
            self.assertFalse(form.is_valid(), value[:20])
        for value in ("-10", "10", "x-3", ""):
            form = AnswerForm(
                {"revision": 0, "first": value, "second": "3"}, kind="squares", step=2,
            )
            self.assertFalse(form.is_valid())
        form = AnswerForm({"revision": 0, "first": 10}, kind="squares", step=1)
        self.assertFalse(form.is_valid())
        self.assertFalse(GenerationForm({"kind": "bad", "creation_key": uuid4()}).is_valid())
        self.assertFalse(GenerationForm({"kind": "common", "creation_key": "bad"}).is_valid())

    def test_invalid_fields_are_associated_with_their_errors(self) -> None:
        form = AnswerForm(
            {"revision": 0, "first": "abc", "second": ""},
            kind="squares", step=2,
        )
        self.assertFalse(form.is_valid())
        for name in ("first", "second"):
            field_id = form[name].auto_id
            self.assertIn(
                f"{field_id}_error",
                form.fields[name].widget.attrs["aria-describedby"].split(),
            )
            self.assertIn(f'id="{field_id}_error"', form.as_div())
        valid = AnswerForm(
            {"revision": 0, "first": 3}, kind="common", step=1,
        )
        self.assertTrue(valid.is_valid())
        self.assertNotIn("id_first_error", valid.as_div())


class FactoringFlowTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username="learner")
        self.other = get_user_model().objects.create_user(username="other")
        self.client.force_login(self.user)
        self.exercise = Exercise.objects.create(
            user=self.user, kind="common", a=6, b=9, creation_key=uuid4(),
        )

    def submit(self, exercise: Exercise, **answers: object):
        exercise.refresh_from_db()
        return self.client.post(reverse("answer_exercise", args=[exercise.pk]), {
            "revision": exercise.revision, **answers,
        })

    def test_two_steps_and_no_future_answers_in_html(self) -> None:
        detail = reverse("exercise", args=[self.exercise.pk])
        response = self.client.get(detail)
        self.assertContains(response, "Passo 1 de 2")
        self.assertNotContains(response, 'name="second"')
        self.assertNotContains(response, "3(2x + 3)")
        self.submit(self.exercise, first=3, second=3, step=2, user_id=self.other.pk)
        response = self.client.get(detail)
        self.assertContains(response, "Passo 2 de 2")
        self.assertContains(response, 'name="second"')
        self.assertNotContains(response, "3(2x + 3)")
        self.submit(self.exercise, first=2, second=3)
        response = self.client.get(detail)
        self.assertContains(response, "3(2x + 3)")
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 3)
        self.assertTrue(self.exercise.first_try)
        self.assertEqual(self.exercise.user, self.user)
        self.assertIsNotNone(self.exercise.completed_at)

    def test_wrong_and_invalid_attempts_preserved_then_retry(self) -> None:
        self.submit(self.exercise, first=2)
        response = self.client.get(reverse("exercise", args=[self.exercise.pk]))
        self.assertContains(response, "um dos coeficientes")
        self.assertContains(response, 'value="2"')
        self.assertContains(response, "Tentar novamente")
        self.submit(self.exercise, first="abc")
        response = self.client.get(reverse("exercise", args=[self.exercise.pk]))
        self.assertContains(response, 'value="abc"')
        self.assertContains(response, "Confira os campos")
        self.submit(self.exercise, first=3)
        self.submit(self.exercise, first=2, second=3)
        self.exercise.refresh_from_db()
        self.assertFalse(self.exercise.first_try)
        self.assertEqual(len(self.exercise.attempts), 4)
        self.assertEqual(self.exercise.attempts[1]["answers"], {"first": "abc"})
        self.assertFalse(self.exercise.attempts[1]["correct"])

    def test_smaller_common_divisor_stays_in_step_one(self) -> None:
        self.exercise.a, self.exercise.b = 12, 18
        self.exercise.save()
        self.submit(self.exercise, first=3)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 1)
        self.assertContains(
            self.client.get(reverse("exercise", args=[self.exercise.pk])), "divisor comum maior",
        )

    def test_squares_accept_both_factor_orders(self) -> None:
        for first, second in ((-3, 3), (3, -3)):
            exercise = Exercise.objects.create(
                user=self.user, kind="squares", a=1, b=9, creation_key=uuid4(),
            )
            self.submit(exercise, first=3)
            self.submit(exercise, first=first, second=second)
            exercise.refresh_from_db()
            self.assertTrue(exercise.first_try)
            self.assertContains(
                self.client.get(reverse("exercise", args=[exercise.pk])), "(x − 3)(x + 3)",
            )

    def test_solution_consultation_closes_without_student_credit(self) -> None:
        self.submit(self.exercise, first=2)
        self.exercise.refresh_from_db()
        url = reverse("view_solution", args=[self.exercise.pk])
        data = {"revision": self.exercise.revision}
        self.client.post(url, data)
        self.client.post(url, data)
        self.exercise.refresh_from_db()
        completion = self.exercise.completed_at
        self.assertTrue(self.exercise.solution_viewed)
        self.assertFalse(self.exercise.first_try)
        self.assertEqual(self.exercise.step, 3)
        self.assertEqual(len(self.exercise.attempts), 1)
        self.submit(self.exercise, first=3)
        self.exercise.refresh_from_db()
        self.assertEqual(len(self.exercise.attempts), 1)
        self.assertEqual(self.exercise.completed_at, completion)
        response = self.client.get(reverse("exercise", args=[self.exercise.pk]))
        self.assertContains(response, "não conta como acerto")

    def test_resend_refresh_and_closed_questions_do_not_duplicate(self) -> None:
        url = reverse("answer_exercise", args=[self.exercise.pk])
        data = {"revision": 0, "first": 3}
        self.client.post(url, data)
        self.client.post(url, data)
        self.client.get(reverse("exercise", args=[self.exercise.pk]))
        self.exercise.refresh_from_db()
        self.assertEqual(len(self.exercise.attempts), 1)
        self.assertEqual(self.exercise.step, 2)
        self.submit(self.exercise, first=2, second=3)
        self.exercise.refresh_from_db()
        completion = self.exercise.completed_at
        self.submit(self.exercise, first=2, second=3)
        self.exercise.refresh_from_db()
        self.assertEqual(len(self.exercise.attempts), 2)
        self.assertEqual(self.exercise.completed_at, completion)

    def test_bad_revision_cannot_skip_or_consult(self) -> None:
        for revision in ("", "bad", "-1", "999", "1" * 100):
            self.client.post(reverse("answer_exercise", args=[self.exercise.pk]), {
                "revision": revision, "first": 3, "step": 2,
            })
            self.client.post(reverse("view_solution", args=[self.exercise.pk]), {
                "revision": revision,
            })
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.step, 1)
        self.assertEqual(self.exercise.attempts, [])

    @patch("core.views.generate_parameters", return_value=(6, 9))
    def test_generation_post_idempotence_and_owner(self, generation_mock) -> None:
        key = uuid4()
        data = {"kind": "common", "creation_key": key, "user_id": self.other.pk}
        first = self.client.post(reverse("generate_exercise"), data)
        second = self.client.post(reverse("generate_exercise"), data)
        self.assertEqual(first.url, second.url)
        exercise = Exercise.objects.get(creation_key=key)
        self.assertEqual(exercise.user, self.user)
        self.assertEqual((exercise.a, exercise.b), (6, 9))
        self.assertEqual(Exercise.objects.count(), 2)
        self.assertEqual(self.client.get(reverse("generate_exercise")).status_code, 405)
        self.client.post(reverse("generate_exercise"), {"kind": "bad", "creation_key": uuid4()})
        self.assertEqual(Exercise.objects.count(), 2)

    def test_other_user_cannot_read_modify_or_see_history(self) -> None:
        self.client.force_login(self.other)
        for name in ("exercise", "answer_exercise", "view_solution"):
            url = reverse(name, args=[self.exercise.pk])
            response = (self.client.get(url) if name == "exercise"
                        else self.client.post(url, {"revision": 0, "first": 3}))
            self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse("student"))
        self.assertNotContains(response, "6x + 9")
        self.assertFalse(response.context["has_exercises"])
        self.assertEqual(list(self.client.get(reverse("practice")).context["active_exercises"]), [])
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.attempts, [])

    def test_anonymous_and_csrf_and_safe_methods(self) -> None:
        paths = [reverse(name) for name in ("factoring_content", "practice", "student")]
        paths.append(reverse("exercise", args=[self.exercise.pk]))
        anonymous = Client()
        for path in paths:
            self.assertEqual(anonymous.get(path).status_code, 302)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        for name in ("answer_exercise", "view_solution", "generate_exercise"):
            url = reverse(name, args=[self.exercise.pk]) if name != "generate_exercise" else reverse(name)
            self.assertEqual(protected.post(url, {"revision": 0}).status_code, 403)
            self.assertEqual(anonymous.post(url).status_code, 302)
            self.assertEqual(self.client.get(url).status_code, 405)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.revision, 0)

    def test_progress_empty_and_calculated_counts(self) -> None:
        empty = self.client.get(reverse("student"))
        self.assertIsNone(empty.context["first_try_percent"])
        self.assertContains(empty, "Você ainda não concluiu questões")
        self.submit(self.exercise, first=3)
        self.submit(self.exercise, first=2, second=3)
        assisted = Exercise.objects.create(
            user=self.user, kind="squares", a=1, b=9, creation_key=uuid4(),
        )
        self.client.post(reverse("view_solution", args=[assisted.pk]), {"revision": 0})
        retried = Exercise.objects.create(
            user=self.user, kind="common", a=6, b=9, creation_key=uuid4(),
        )
        self.submit(retried, first=2)
        self.submit(retried, first=3)
        self.submit(retried, first=2, second=3)
        response = self.client.get(reverse("student"))
        self.assertEqual(response.context["completed_count"], 3)
        self.assertEqual(response.context["first_try_count"], 1)
        self.assertAlmostEqual(response.context["first_try_percent"], 100 / 3)
        self.assertEqual(response.context["consultation_count"], 1)
        self.assertContains(response, "33,3%")
        self.assertContains(response, "Resolução consultada")
        self.assertEqual(len(response.context["recent_exercises"]), 3)


class ConcurrentSubmissionTests(TransactionTestCase):
    def test_only_one_simultaneous_completion_is_saved(self) -> None:
        user = get_user_model().objects.create_user(username="concurrent")
        exercise = Exercise.objects.create(
            user=user, kind="common", a=6, b=9, step=2,
            creation_key=uuid4(),
            attempts=[{"step": 1, "answers": {"first": "3"}, "correct": True}],
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
                        "step": 2, "answers": {"first": "2", "second": "3"},
                        "correct": True,
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
