from math import gcd, isqrt
from random import randint

COMMON_MAX = 30
ROOT_MIN = 2
ROOT_MAX = 9


def generate_parameters(kind: str) -> tuple[int, int]:
    if kind == "common":
        factor = randint(2, 5)
        return factor * randint(1, 6), factor * randint(1, 6)
    if kind == "squares":
        root = randint(ROOT_MIN, ROOT_MAX)
        return 1, root * root
    raise ValueError("Tipo de fatoração desconhecido.")


def check_answer(
    kind: str, a: int, b: int, step: int, answers: dict[str, int],
) -> tuple[bool, str]:
    if kind == "common":
        factor = gcd(a, b)
        if step == 1:
            value = answers["first"]
            if value == factor:
                return True, "Correto! Agora divida os dois coeficientes pelo fator retirado."
            if a % value == 0 and b % value == 0:
                return False, "Existe um divisor comum maior. Procure o maior fator comum."
            if (a % value == 0) != (b % value == 0):
                return False, "Esse número divide um dos coeficientes, mas não divide o outro."
            return False, "Procure um número que divida os dois coeficientes sem deixar resto."
        if step == 2:
            correct = answers["first"] == a // factor and answers["second"] == b // factor
            return correct, (
                "Correto! Você retirou o maior fator comum."
                if correct else "Confira a divisão de cada coeficiente pelo fator retirado."
            )
    elif kind == "squares":
        root = isqrt(b)
        if step == 1:
            correct = answers["first"] == root
            return correct, (
                "Correto! Agora complete os dois fatores."
                if correct else f"Qual número positivo multiplicado por ele mesmo resulta em {b}?"
            )
        if step == 2:
            correct = sorted(answers.values()) == [-root, root]
            return correct, (
                "Correto! O produto dos fatores reproduz a diferença de quadrados."
                if correct else "Use a raiz encontrada com sinais opostos: um negativo e um positivo."
            )
    raise ValueError("Tipo ou passo de fatoração inválido.")


def solution(kind: str, a: int, b: int) -> tuple[str, str]:
    if kind == "common":
        factor = gcd(a, b)
        return (
            f"{factor}({a // factor}x + {b // factor})",
            f"O MDC de {a} e {b} é {factor}. Dividindo: "
            f"{a} ÷ {factor} = {a // factor} e {b} ÷ {factor} = {b // factor}.",
        )
    if kind == "squares":
        root = isqrt(b)
        return (
            f"(x − {root})(x + {root})",
            f"Como {b} = {root}², aplicamos x² − n² = (x − n)(x + n).",
        )
    raise ValueError("Tipo de fatoração desconhecido.")
