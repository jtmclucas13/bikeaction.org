from django.urls import path

from projects import views

urlpatterns = [
    path("application/", views.project_application, name="project_application_form"),
    path("application/<pk>/edit", views.project_application, name="project_application_edit"),
    path(
        "application/<pk>/delete",
        views.project_application_delete,
        name="project_application_delete",
    ),
    path("application/<pk>/view", views.project_application_view, name="project_application_view"),
]
