from math import isqrt
from random import choice, randint

ROOT_MAX = 6   # raízes de -6 a 6
COEFF_MAX = 3  # coeficiente a de -3 a 3 (exceto zero)


def generate_parameters() -> tuple[int, int, int, int]:
    """Retorna (a, b, c, delta) com raízes inteiras garantidas."""
    a = choice([v for v in range(-COEFF_MAX, COEFF_MAX + 1) if v != 0])
    x1 = randint(-ROOT_MAX, ROOT_MAX)
    x2 = randint(-ROOT_MAX, ROOT_MAX)
    # ax² + bx + c = a(x - x1)(x - x2)  →  b = -a(x1+x2), c = a*x1*x2
    b = -a * (x1 + x2)
    c = a * x1 * x2
    delta = b * b - 4 * a * c  # sempre >= 0 por construção
    return a, b, c, delta


def expression(a: int, b: int, c: int) -> str:
    """Formata ax² + bx + c = 0 de forma didática."""
    if a == 1:
        expr = "x²"
    elif a == -1:
        expr = "−x²"
    else:
        expr = f"{a}x²".replace("-", "−")
    if b > 0:
        expr += f" + {b}x"
    elif b < 0:
        expr += f" − {abs(b)}x"
    if c > 0:
        expr += f" + {c}"
    elif c < 0:
        expr += f" − {abs(c)}"
    return expr + " = 0"


def roots(a: int, b: int, delta: int) -> tuple[int, int]:
    """Retorna (x_menor, x_maior). Funciona com a positivo ou negativo."""
    sq = isqrt(delta)
    r1 = (-b - sq) // (2 * a)
    r2 = (-b + sq) // (2 * a)
    return (min(r1, r2), max(r1, r2))


def check_answer(
    a: int, b: int, c: int, delta: int, step: int, answers: dict,
) -> tuple[bool, str]:
    if step == 1:
        # answers["first"] pode ser int (form validado) ou str (JSON de tentativa)
        given = int(answers["first"])
        if given == delta:
            return True, "Correto! Agora aplique a fórmula para encontrar as raízes."
        wrong_sign = b * b + 4 * a * c  # erro comum: sinal de 4ac trocado
        if given == wrong_sign:
            return False, "Confira o sinal: Δ = b² − 4ac (menos, não mais)."
        return False, f"Recalcule: b² = {b*b}, 4ac = {4*a*c}. Então Δ = b² − 4ac."

    # step == 2
    x1, x2 = roots(a, b, delta)
    given = sorted([int(answers["first"]), int(answers["second"])])
    correct = [x1, x2]  # já ordenado por roots()
    if given == correct:
        return True, "Correto! Você resolveu a equação do segundo grau."
    if given == sorted([-x1, -x2]):
        return False, "Os sinais estão invertidos. Use x = (−b ± √Δ) ÷ (2a)."
    return False, (
        f"Use x = (−b ± √Δ) ÷ (2a). "
        f"√Δ = {isqrt(delta)}, −b = {-b}, 2a = {2*a}."
    )


def solution(a: int, b: int, c: int, delta: int) -> tuple[str, str, str]:
    sq = isqrt(delta)
    x1, x2 = roots(a, b, delta)
    step1 = f"Δ = b² − 4ac = ({b})² − 4·({a})·({c}) = {b*b} − {4*a*c} = {delta}"
    if x1 == x2:
        step2 = f"x = −b ÷ (2a) = ({-b}) ÷ ({2*a}) = {x1}  (raiz dupla)"
        result = f"x = {x1}"
    else:
        step2 = (
            f"x = (−b ± √Δ) ÷ (2a) = ({-b} ± {sq}) ÷ ({2*a})\n"
            f"x₁ = ({-b} − {sq}) ÷ ({2*a}) = {x1}\n"
            f"x₂ = ({-b} + {sq}) ÷ ({2*a}) = {x2}"
        )
        result = f"x₁ = {x1}  e  x₂ = {x2}"
    verify = (
        f"Verificação: {a}·({x1})² + ({b})·({x1}) + ({c}) = "
        f"{a*x1*x1 + b*x1 + c} ✓"
    )
    return result, f"{step1}\n{step2}", verify


def delta_hint(a: int, b: int, c: int) -> str:
    b_sq = b * b
    four_ac = 4 * a * c
    return (
        f"Δ = b² − 4ac, onde a = {a}, b = {b}, c = {c}. "
        f"Calcule ({b})² − 4·({a})·({c}) = {b_sq} − ({four_ac})."
    )
