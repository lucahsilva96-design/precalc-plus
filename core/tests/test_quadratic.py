"""Testes para o módulo quadratic — cobre geração, lógica, bugs corrigidos e integração DB."""
from math import isqrt

from django.contrib.auth import get_user_model
from django.test import TestCase

from core import quadratic
from core.models import Exercise

User = get_user_model()


# ---------------------------------------------------------------------------
# Geração de parâmetros
# ---------------------------------------------------------------------------

class GenerateParametersTest(TestCase):
    def _assert_valid(self, a, b, c, delta):
        self.assertNotEqual(a, 0)
        self.assertGreaterEqual(abs(a), 1)
        self.assertLessEqual(abs(a), 3)
        self.assertEqual(delta, b * b - 4 * a * c)
        self.assertGreaterEqual(delta, 0)
        self.assertEqual(isqrt(delta) ** 2, delta, "delta deve ser quadrado perfeito")

    def test_generates_valid_params(self):
        for _ in range(200):
            self._assert_valid(*quadratic.generate_parameters())

    def test_roots_satisfy_equation(self):
        """Bug fix: roots() com a negativo deve continuar correto."""
        for _ in range(200):
            a, b, c, delta = quadratic.generate_parameters()
            x1, x2 = quadratic.roots(a, b, delta)
            self.assertEqual(a * x1 * x1 + b * x1 + c, 0,
                             f"x1={x1} não satisfaz {a}x²+{b}x+{c}")
            self.assertEqual(a * x2 * x2 + b * x2 + c, 0,
                             f"x2={x2} não satisfaz {a}x²+{b}x+{c}")

    def test_roots_ordered(self):
        """roots() deve retornar (menor, maior) independente do sinal de a."""
        for _ in range(200):
            a, b, c, delta = quadratic.generate_parameters()
            x1, x2 = quadratic.roots(a, b, delta)
            self.assertLessEqual(x1, x2)


# ---------------------------------------------------------------------------
# Formatação de expressão
# ---------------------------------------------------------------------------

class ExpressionTest(TestCase):
    def test_positive_a_b_c(self):
        self.assertEqual(quadratic.expression(2, 3, 1), "2x² + 3x + 1 = 0")

    def test_a_one(self):
        self.assertEqual(quadratic.expression(1, -5, 6), "x² − 5x + 6 = 0")

    def test_a_minus_one(self):
        self.assertEqual(quadratic.expression(-1, 0, 4), "−x² + 4 = 0")

    def test_negative_a(self):
        self.assertIn("−2x²", quadratic.expression(-2, 3, -1))

    def test_zero_b_omitted(self):
        """Bug fix: b=0 não deve aparecer como '0x'."""
        self.assertNotIn("0x", quadratic.expression(1, 0, -9))

    def test_zero_c_omitted(self):
        """Bug fix: c=0 não deve aparecer como '+ 0'."""
        self.assertNotIn("+ 0", quadratic.expression(1, -3, 0))
        self.assertNotIn("− 0", quadratic.expression(1, -3, 0))


# ---------------------------------------------------------------------------
# check_answer — step 1 (delta)
# ---------------------------------------------------------------------------

class CheckAnswerStep1Test(TestCase):
    # x² − 7x + 12 = 0  →  a=1, b=−7, c=12, delta=49−48=1
    A, B, C, DELTA = 1, -7, 12, 1

    def test_correct_int(self):
        ok, _ = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 1, {"first": 1})
        self.assertTrue(ok)

    def test_correct_string(self):
        """Bug fix: answers["first"] vindo do JSON de tentativas é string."""
        ok, _ = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 1, {"first": "1"})
        self.assertTrue(ok)

    def test_wrong_sign_hint(self):
        wrong = self.B * self.B + 4 * self.A * self.C
        ok, msg = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 1, {"first": wrong})
        self.assertFalse(ok)
        self.assertIn("sinal", msg)

    def test_random_wrong(self):
        ok, _ = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 1, {"first": 999})
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# check_answer — step 2 (raízes)
# ---------------------------------------------------------------------------

class CheckAnswerStep2Test(TestCase):
    # x² − 5x + 6 = 0  →  x1=2, x2=3, delta=1
    A, B, C, DELTA = 1, -5, 6, 1

    def test_correct_order1(self):
        ok, _ = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 2,
                                       {"first": 2, "second": 3})
        self.assertTrue(ok)

    def test_correct_order2_reversed(self):
        """Ordem dos campos não deve importar."""
        ok, _ = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 2,
                                       {"first": 3, "second": 2})
        self.assertTrue(ok)

    def test_string_answers(self):
        """Bug fix: answers vindo do JSON de tentativas são strings."""
        ok, _ = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 2,
                                       {"first": "2", "second": "3"})
        self.assertTrue(ok)

    def test_inverted_signs_hint(self):
        ok, msg = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 2,
                                         {"first": -2, "second": -3})
        self.assertFalse(ok)
        self.assertIn("sinais", msg)

    def test_wrong_roots(self):
        ok, _ = quadratic.check_answer(self.A, self.B, self.C, self.DELTA, 2,
                                       {"first": 0, "second": 0})
        self.assertFalse(ok)

    def test_negative_a_correct(self):
        """Bug fix: a negativo — roots() retorna na ordem certa."""
        # −x² + 5x − 6 = 0  →  a=−1, b=5, c=−6, raízes 2 e 3
        a, b, c, delta = -1, 5, -6, 25 - 24
        ok, _ = quadratic.check_answer(a, b, c, delta, 2, {"first": 2, "second": 3})
        self.assertTrue(ok)


# ---------------------------------------------------------------------------
# solution()
# ---------------------------------------------------------------------------

class SolutionTest(TestCase):
    def test_two_distinct_roots(self):
        result, explanation, verify = quadratic.solution(1, -5, 6, 1)
        self.assertIn("2", result)
        self.assertIn("3", result)
        self.assertIn("Δ", explanation)
        self.assertIn("✓", verify)

    def test_double_root(self):
        # x² − 4x + 4 = 0  →  raiz dupla x=2, delta=0
        result, explanation, verify = quadratic.solution(1, -4, 4, 0)
        self.assertIn("dupla", explanation)
        self.assertIn("2", result)

    def test_verify_is_zero(self):
        """Verificação deve sempre dar zero."""
        for _ in range(50):
            a, b, c, delta = quadratic.generate_parameters()
            result, _, verify = quadratic.solution(a, b, c, delta)
            self.assertIn("✓", verify)


# ---------------------------------------------------------------------------
# Integração com Exercise (DB)
# ---------------------------------------------------------------------------

class ExerciseQuadraticIntegrationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pw")

    def _make(self, a=1, b=-5, c=6):
        import uuid
        return Exercise.objects.create(
            user=self.user, kind=Exercise.Kind.QUADRATIC,
            a=a, b=b, c=c, creation_key=uuid.uuid4(),
        )

    def test_expression_renders(self):
        ex = self._make()
        self.assertIn("x²", ex.expression)

    def test_constraint_a_zero_rejected(self):
        import uuid
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Exercise.objects.create(
                user=self.user, kind=Exercise.Kind.QUADRATIC,
                a=0, b=0, c=0, creation_key=uuid.uuid4(),
            )

    def test_delta_recalculated_correctly(self):
        ex = self._make(a=1, b=-5, c=6)
        self.assertEqual(ex.b * ex.b - 4 * ex.a * ex.c, 1)

    def test_isolation_from_linear(self):
        import uuid
        lin = Exercise.objects.create(
            user=self.user, kind=Exercise.Kind.LINEAR,
            a=2, b=3, c=7, creation_key=uuid.uuid4(),
        )
        quad = self._make()
        qs_q = list(Exercise.objects.filter(kind=Exercise.Kind.QUADRATIC))
        qs_l = list(Exercise.objects.filter(kind=Exercise.Kind.LINEAR))
        self.assertIn(quad, qs_q)
        self.assertNotIn(lin, qs_q)
        self.assertIn(lin, qs_l)
        self.assertNotIn(quad, qs_l)
