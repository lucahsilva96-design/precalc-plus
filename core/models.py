from math import isqrt

from django.conf import settings
from django.db import models
from django.db.models import Q

from . import equations, quadratic


class Exercise(models.Model):
    class Kind(models.TextChoices):
        COMMON = "common", "Fator comum"
        SQUARES = "squares", "Diferença de quadrados"
        LINEAR = "linear", "Equação do primeiro grau"
        QUADRATIC = "quadratic", "Equação do segundo grau"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=9, choices=Kind.choices)
    a = models.SmallIntegerField()
    b = models.SmallIntegerField()
    c = models.SmallIntegerField(null=True, blank=True)
    step = models.PositiveSmallIntegerField(default=1)
    revision = models.PositiveIntegerField(default=0)
    creation_key = models.UUIDField()
    attempts = models.JSONField(default=list)
    solution_viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "creation_key"], name="unique_exercise_creation",
            ),
            models.CheckConstraint(
                condition=Q(step__in=[1, 2, 3]), name="exercise_valid_step",
            ),
            models.CheckConstraint(
                condition=(Q(step=3, completed_at__isnull=False)
                           | Q(step__in=[1, 2], completed_at__isnull=True)),
                name="exercise_completion_matches_step",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind__in=["common", "squares"], a__gte=1,
                      b__gte=1, c__isnull=True)
                    | (Q(kind="linear", a__gte=-5, a__lte=5,
                         b__gte=-10, b__lte=10, c__isnull=False,
                         c__gte=-55, c__lte=55) & ~Q(a=0))
                    | (Q(kind="quadratic", a__gte=-3, a__lte=3,
                         b__gte=-36, b__lte=36, c__isnull=False,
                         c__gte=-108, c__lte=108) & ~Q(a=0))
                ),
                name="exercise_valid_parameters",
            ),
        ]

    @property
    def expression(self) -> str:
        if self.kind == self.Kind.LINEAR:
            return equations.expression(self.a, self.b, self.c)
        if self.kind == self.Kind.QUADRATIC:
            return quadratic.expression(self.a, self.b, self.c)
        if self.kind == self.Kind.COMMON:
            return f"{self.a}x + {self.b}"
        return f"x² − {self.b}"

    @property
    def first_try(self) -> bool:
        return bool(
            self.completed_at and not self.solution_viewed
            and len(self.attempts) == 2
            and all(attempt["correct"] for attempt in self.attempts)
        )

    @property
    def result_label(self) -> str:
        if self.solution_viewed:
            return "Resolução consultada · não conta como acerto"
        if not self.completed_at:
            return "Em andamento"
        if self.first_try:
            return "Correta na primeira tentativa"
        return "Concluída após novas tentativas"

    @property
    def root(self) -> int:
        return isqrt(self.b)
