from django.contrib import admin
from django.urls import include, path

from core import views

urlpatterns = [
    path("", views.home, name="home"),
    path("aluno/", views.student, name="student"),
    path("equacoes/", views.equations_content, name="equations_content"),
    path("quadratica/", views.quadratic_content, name="quadratic_content"),
    path("fatoracao/", views.factoring_content, name="factoring_content"),
    path("praticar/", views.practice, name="practice"),
    path("fatoracao/praticar/", views.practice),
    path("fatoracao/gerar/", views.generate_exercise, name="generate_exercise"),
    path("fatoracao/questao/<int:pk>/", views.exercise_detail, name="exercise"),
    path("fatoracao/questao/<int:pk>/responder/", views.answer_exercise, name="answer_exercise"),
    path("fatoracao/questao/<int:pk>/resolucao/", views.view_solution, name="view_solution"),
    path("accounts/google/login/", views.google_login, name="google_login"),
    path("accounts/google/login/callback/", views.google_callback, name="google_callback"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
]
