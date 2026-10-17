from typing import Any

from django import forms

from .equations import RIGHT_SIDE_MAX, SOLUTION_MAX
from .factoring import COMMON_MAX, ROOT_MAX
from .quadratic import ROOT_MAX as QUAD_ROOT_MAX
from .models import Exercise


class GenerationForm(forms.Form):
    kind = forms.ChoiceField(
        label="Tipo de questão", choices=Exercise.Kind.choices,
    )
    creation_key = forms.UUIDField(widget=forms.HiddenInput)


class StateForm(forms.Form):
    revision = forms.IntegerField(
        min_value=0, max_value=2147483647, widget=forms.HiddenInput,
    )


class AnswerForm(StateForm):
    first = forms.IntegerField(
        label="Resposta", min_value=1, max_value=COMMON_MAX,
    )

    def __init__(
        self, *args: Any, kind: str, step: int, **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if kind == Exercise.Kind.LINEAR:
            limit = RIGHT_SIDE_MAX if step == 1 else SOLUTION_MAX
            self.fields["first"] = forms.IntegerField(
                label="Valor de c − b" if step == 1 else "Valor de x",
                min_value=-limit, max_value=limit,
            )
        elif kind == Exercise.Kind.COMMON:
            self.fields["first"].label = (
                "Maior fator comum" if step == 1
                else "Coeficiente de x nos parênteses"
            )
            if step == 2:
                self.fields["second"] = forms.IntegerField(
                    label="Termo constante nos parênteses",
                    min_value=1, max_value=COMMON_MAX,
                )
        elif kind == Exercise.Kind.QUADRATIC:
            if step == 1:
                self.fields["first"] = forms.IntegerField(
                    label="Valor do discriminante (Δ)",
                    min_value=0, max_value=5000,
                )
            else:
                self.fields["first"] = forms.IntegerField(
                    label="Primeira raiz (x₁)",
                    min_value=-QUAD_ROOT_MAX, max_value=QUAD_ROOT_MAX,
                )
                self.fields["second"] = forms.IntegerField(
                    label="Segunda raiz (x₂)",
                    min_value=-QUAD_ROOT_MAX, max_value=QUAD_ROOT_MAX,
                )
        elif step == 1:
            self.fields["first"] = forms.IntegerField(
                label="Raiz quadrada positiva do termo constante",
                min_value=1, max_value=ROOT_MAX,
            )
        else:
            self.fields["first"] = forms.IntegerField(
                label="Número com sinal no primeiro fator (x + número)",
                min_value=-ROOT_MAX, max_value=ROOT_MAX,
            )
            self.fields["second"] = forms.IntegerField(
                label="Número com sinal no segundo fator (x + número)",
                min_value=-ROOT_MAX, max_value=ROOT_MAX,
            )
        for name in ("first", "second"):
            if name in self.fields:
                self.fields[name].widget = forms.TextInput(attrs={
                    "inputmode": (
                        "text" if kind == "linear"
                        or (step == 2 and kind in ("squares", "quadratic"))
                        else "numeric"
                    ),
                    "maxlength": "6", "autocomplete": "off",
                    "aria-describedby": "answer-format feedback",
                })

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        for name in ("first", "second", "revision"):
            max_length = 10 if name == "revision" else 6
            if (name in self.fields
                    and len(str(self.data.get(name, ""))) > max_length):
                self.add_error(
                    name,
                    "A resposta é longa demais. "
                    "Use apenas um número inteiro curto.",
                )
        # Um aria-describedby próprio substitui a associação automática
        # do Django. Incluímos também o erro do campo, quando ele existe.
        for name in ("first", "second"):
            if name in self.errors:
                self.fields[name].widget.attrs["aria-describedby"] = (
                    f"answer-format feedback {self[name].auto_id}_error"
                )
        return cleaned
