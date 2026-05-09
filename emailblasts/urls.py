from django.urls import path

from emailblasts.views import (
    email_blast_list,
    email_draft,
    email_draft_image,
    email_draft_preview,
)

urlpatterns = [
    path("", email_draft, name="email_draft"),
    path("blasts/", email_blast_list, name="email_blast_list"),
    path("<int:draft_id>/", email_draft, name="email_draft_edit"),
    path("preview/", email_draft_preview, name="email_draft_preview"),
    path("image/<str:filename>", email_draft_image, name="email_draft_image"),
]
