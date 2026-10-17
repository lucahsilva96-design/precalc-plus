from math import gcd
from uuid import uuid4

from allauth.socialaccount.providers.google.views import (
    oauth2_callback,
    oauth2_login,
)
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import equations, quadratic
from .factoring import check_answer, generate_parameters, solution
from .forms import AnswerForm, GenerationForm, StateForm
from .models import Exercise

TOPICS = (
    ("01", "Fatoração", "Reconheça padrões e transforme expressões algébricas.", "a² − b²"),
    ("02", "Equações", "Explore incógnitas e relações de igualdade.", "2x + 3 = 7"),
    ("03", "Funções", "Entenda como uma grandeza depende de outra.", "f(x) = x²"),
    ("04", "Trigonometria", "Relacione ângulos, triângulos e razões.", "sen θ"),
    ("05", "Limites básicos", "Conheça a ideia de aproximação e continuidade.", "x → a"),
)


def site_context(request: HttpRequest) -> dict[str, object]:
    return {"google_configured": settings.GOOGLE_CONFIGURED, "topics": TOPICS}


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html")


@login_required
def student(request: HttpRequest) -> HttpResponse:
    module = request.GET.get("module", "all")
    if module not in ("all", "factoring", "equations", "quadratic"):
        module = "all"
    queryset = Exercise.objects.filter(user=request.user)
    if module == "equations":
        queryset = queryset.filter(kind=Exercise.Kind.LINEAR)
    elif module == "quadratic":
        queryset = queryset.filter(kind=Exercise.Kind.QUADRATIC)
    elif module == "factoring":
        queryset = queryset.filter(kind__in=[Exercise.Kind.COMMON, Exercise.Kind.SQUARES])
    exercises = list(queryset)
    completed = [exercise for exercise in exercises if exercise.completed_at]
    first_try = sum(exercise.first_try for exercise in completed)
    return render(request, "core/student.html", {
        "selected_module": module,
        "completed_count": len(completed),
        "first_try_count": first_try,
        "first_try_percent": 100 * first_try / len(completed) if completed else None,
        "consultation_count": sum(exercise.solution_viewed for exercise in exercises),
        "recent_exercises": exercises[:10],
        "has_exercises": bool(exercises),
    })


def google_login(request: HttpRequest) -> HttpResponse:
    if not settings.GOOGLE_CONFIGURED:
        return render(request, "account/login.html", status=503)
    return oauth2_login(request)


def google_callback(request: HttpRequest) -> HttpResponse:
    if not settings.GOOGLE_CONFIGURED:
        return render(request, "account/login.html", status=503)
    return oauth2_callback(request)


@login_required
@require_GET
def factoring_content(request: HttpRequest) -> HttpResponse:
    return render(request, "core/factoring_content.html")


@login_required
@require_GET
def practice(request: HttpRequest) -> HttpResponse:
    kind = request.GET.get("kind", Exercise.Kind.COMMON)
    if kind not in Exercise.Kind.values:
        kind = Exercise.Kind.COMMON
    return render(request, "core/practice.html", {
        "generation_form": GenerationForm(initial={
            "creation_key": uuid4(), "kind": kind,
        }),
        "active_exercises": Exercise.objects.filter(
            user=request.user, completed_at__isnull=True,
        )[:5],
    })


@login_required
@require_POST
def generate_exercise(request: HttpRequest) -> HttpResponse:
    form = GenerationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Escolha um tipo válido e use o formulário atualizado.")
        return redirect("practice")
    kind = form.cleaned_data["kind"]
    c = None
    if kind == Exercise.Kind.LINEAR:
        a, b, c = equations.generate_parameters()
    elif kind == Exercise.Kind.QUADRATIC:
        a, b, c, _delta = quadratic.generate_parameters()
    else:
        a, b = generate_parameters(kind)
    exercise, _ = Exercise.objects.get_or_create(
        user=request.user, creation_key=form.cleaned_data["creation_key"],
        defaults={"kind": kind, "a": a, "b": b, "c": c},
    )
    return redirect("exercise", pk=exercise.pk)


@login_required
@require_GET
def exercise_detail(request: HttpRequest, pk: int) -> HttpResponse:
    exercise = get_object_or_404(Exercise, pk=pk, user=request.user)
    context = {
        "exercise": exercise,
        "generation_form": GenerationForm(initial={
            "kind": exercise.kind, "creation_key": uuid4(),
        }),
    }
    if exercise.completed_at:
        if exercise.kind == Exercise.Kind.LINEAR:
            (context["equation_solution"], context["explanation"],
             context["verification"]) = equations.solution(
                exercise.a, exercise.b, exercise.c,
            )
        elif exercise.kind == Exercise.Kind.QUADRATIC:
            delta = exercise.b * exercise.b - 4 * exercise.a * exercise.c
            (context["equation_solution"], context["explanation"],
             context["verification"]) = quadratic.solution(
                exercise.a, exercise.b, exercise.c, delta,
            )
        else:
            context["factorization"], context["explanation"] = solution(
                exercise.kind, exercise.a, exercise.b,
            )
    else:
        form = AnswerForm(
            kind=exercise.kind, step=exercise.step,
            initial={"revision": exercise.revision},
        )
        feedback = ""
        last = exercise.attempts[-1] if exercise.attempts else None
        if last:
            if last["step"] == exercise.step:
                form = AnswerForm(
                    {**last["answers"], "revision": exercise.revision},
                    kind=exercise.kind, step=exercise.step,
                )
                if not form.is_valid():
                    feedback = "Confira os campos indicados e tente novamente."
                else:
                    _, feedback = check_exercise_answer(
                        exercise,
                        {name: form.cleaned_data[name]
                         for name in last["answers"]},
                    )
            else:
                feedback = "Passo 1 correto! Continue a resolução."
        if exercise.kind == Exercise.Kind.COMMON and exercise.step == 2:
            context["common_factor"] = gcd(exercise.a, exercise.b)
        if exercise.kind == Exercise.Kind.LINEAR:
            context["inverse_operation"] = equations.inverse_operation(exercise.b)
            context["x_term"] = equations.x_term(exercise.a)
            if exercise.step == 2:
                context["equation_right_side"] = exercise.c - exercise.b
        if exercise.kind == Exercise.Kind.QUADRATIC:
            delta = exercise.b * exercise.b - 4 * exercise.a * exercise.c
            context["quadratic_delta_hint"] = quadratic.delta_hint(
                exercise.a, exercise.b, exercise.c,
            )
            if exercise.step == 2:
                context["quadratic_delta"] = delta
        context.update({
            "answer_form": form, "feedback": feedback,
            "state_form": StateForm(initial={"revision": exercise.revision}),
        })
    return render(request, "core/exercise.html", context)


def save_exercise_state(exercise: Exercise, **changes: object) -> bool:
    # SQLite não bloqueia linhas via select_for_update. Um único UPDATE
    # condicional troca a revisão e os dados juntos; só um envio pode vencer.
    return bool(Exercise.objects.filter(
        pk=exercise.pk, user=exercise.user, revision=exercise.revision,
        completed_at__isnull=True,
    ).update(revision=exercise.revision + 1, **changes))


def valid_submission(request: HttpRequest, exercise: Exercise) -> bool:
    form = StateForm(request.POST)
    if (exercise.completed_at or not form.is_valid()
            or form.cleaned_data["revision"] != exercise.revision):
        messages.info(request, "Esta questão mudou ou já foi encerrada. Confira o estado atual.")
        return False
    return True


@login_required
@require_POST
def answer_exercise(request: HttpRequest, pk: int) -> HttpResponse:
    exercise = get_object_or_404(Exercise, pk=pk, user=request.user)
    if not valid_submission(request, exercise):
        return redirect("exercise", pk=pk)
    form = AnswerForm(request.POST, kind=exercise.kind, step=exercise.step)
    correct = False
    if form.is_valid():
        correct, _ = check_exercise_answer(
            exercise,
            {name: form.cleaned_data[name] for name in ("first", "second")
             if name in form.fields},
        )
    # Entradas rejeitadas também contam como tentativas. Limite de armazenamento
    # evita persistir payloads abusivos; respostas normais são preservadas inteiras.
    answers = {
        name: str(request.POST.get(name, ""))[:64]
        for name in ("first", "second") if name in form.fields
    }
    attempts = exercise.attempts + [{
        "step": exercise.step, "answers": answers, "correct": correct,
    }]
    next_step = exercise.step + 1 if correct else exercise.step
    if not save_exercise_state(
        exercise, attempts=attempts, step=next_step,
        completed_at=timezone.now() if next_step == 3 else None,
    ):
        messages.info(request, "Outro envio já foi processado. Confira o estado atual.")
    return redirect("exercise", pk=pk)


@login_required
@require_POST
def view_solution(request: HttpRequest, pk: int) -> HttpResponse:
    exercise = get_object_or_404(Exercise, pk=pk, user=request.user)
    if valid_submission(request, exercise):
        if not save_exercise_state(
            exercise, step=3, completed_at=timezone.now(), solution_viewed=True,
        ):
            messages.info(request, "Outro envio já foi processado. Confira o estado atual.")
    return redirect("exercise", pk=pk)


@login_required
@require_GET
def equations_content(request: HttpRequest) -> HttpResponse:
    return render(request, "core/equations_content.html")


@login_required
@require_GET
def quadratic_content(request: HttpRequest) -> HttpResponse:
    return render(request, "core/quadratic_content.html")


def check_exercise_answer(
    exercise: Exercise, answers: dict[str, int],
) -> tuple[bool, str]:
    if exercise.kind == Exercise.Kind.LINEAR:
        return equations.check_answer(
            exercise.a, exercise.b, exercise.c, exercise.step, answers["first"],
        )
    if exercise.kind == Exercise.Kind.QUADRATIC:
        delta = exercise.b * exercise.b - 4 * exercise.a * exercise.c
        return quadratic.check_answer(
            exercise.a, exercise.b, exercise.c, delta, exercise.step, answers,
        )
    return check_answer(
        exercise.kind, exercise.a, exercise.b, exercise.step, answers,
    )
