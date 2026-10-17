from random import choice, randint

COEFFICIENT_MAX = 5
CONSTANT_MAX = 10
SOLUTION_MAX = 9
RIGHT_SIDE_MAX = COEFFICIENT_MAX * SOLUTION_MAX


def generate_parameters() -> tuple[int, int, int]:
    a = choice([
        value for value in range(-COEFFICIENT_MAX, COEFFICIENT_MAX + 1)
        if value != 0
    ])
    b = randint(-CONSTANT_MAX, CONSTANT_MAX)
    x = randint(-SOLUTION_MAX, SOLUTION_MAX)
    return a, b, a * x + b


def x_term(a: int) -> str:
    if a == 1:
        return "x"
    if a == -1:
        return "−x"
    return f"{a}x".replace("-", "−")


def expression(a: int, b: int, c: int) -> str:
    term = x_term(a)
    if b > 0:
        term += f" + {b}"
    elif b < 0:
        term += f" − {abs(b)}"
    return f"{term} = {c}".replace("-", "−")


def inverse_operation(b: int) -> str:
    if b > 0:
        return f"Subtraia {b} dos dois lados."
    if b < 0:
        return f"Some {abs(b)} aos dois lados."
    return "O termo constante é zero; os dois lados já estão sem ele."


def check_answer(
    a: int, b: int, c: int, step: int, answer: int,
) -> tuple[bool, str]:
    right_side = c - b
    expected = right_side if step == 1 else right_side // a
    if step not in (1, 2):
        raise ValueError("Passo de equação inválido.")
    if answer == expected:
        return True, "Correto! Você aplicou a operação aos dois lados."
    if step == 1:
        if b != 0 and answer == c + b:
            return False, (
                "Você informou c + b. Para retirar o termo constante, "
                "calcule c − b, aplicando a mesma operação aos dois lados."
            )
        return False, inverse_operation(b) + " Confira o valor do lado direito."
    if expected != 0 and answer == -expected:
        return False, (
            "O valor informado tem o sinal oposto. "
            "Confira os sinais da divisão."
        )
    return False, (
        "Divida o lado direito e o coeficiente de x por a. "
        "Confira a divisão."
    )


def solution(a: int, b: int, c: int) -> tuple[str, str, str]:
    right_side = c - b
    x = right_side // a
    return (
        f"{x_term(a)} = {right_side}; x = {x}",
        f"{inverse_operation(b)} Obtemos {x_term(a)} = {right_side}. "
        f"Depois dividimos os dois lados por {a}: x = {x}.",
        f"Conferência: ({a}) × ({x}) + ({b}) = {c}. "
        f"O lado esquerdo vale {a * x + b}, igual ao lado direito.",
    )
