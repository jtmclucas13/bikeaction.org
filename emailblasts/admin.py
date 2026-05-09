from django.contrib import admin, messages
from django.db import transaction

from emailblasts.models import (
    EmailBlast,
    EmailBlastDelivery,
    EmailBlastTarget,
    EmailBlastTargetNode,
)
from emailblasts.tasks import send_email_blast


def _mark_email_blast_status(modeladmin, request, queryset, status):
    updated = queryset.update(status=status)
    modeladmin.message_user(
        request,
        f"{updated} email blast{'s' if updated != 1 else ''} marked as "
        f"{EmailBlast.Status(status).label.lower()}.",
    )


@admin.action(description="Mark selected email blasts as draft")
def mark_as_draft(modeladmin, request, queryset):
    _mark_email_blast_status(modeladmin, request, queryset, EmailBlast.Status.DRAFT)


@admin.action(description="Mark selected email blasts as submitted")
def mark_as_submitted(modeladmin, request, queryset):
    _mark_email_blast_status(modeladmin, request, queryset, EmailBlast.Status.SUBMITTED)


@admin.action(description="Approve selected email blasts")
def mark_as_approved(modeladmin, request, queryset):
    _mark_email_blast_status(modeladmin, request, queryset, EmailBlast.Status.APPROVED)


@admin.action(description="Reject selected email blasts")
def mark_as_rejected(modeladmin, request, queryset):
    _mark_email_blast_status(modeladmin, request, queryset, EmailBlast.Status.REJECTED)


@admin.action(description="Send selected approved email blasts")
def send_selected_email_blasts(modeladmin, request, queryset):
    approved_blast_ids = list(
        queryset.filter(status=EmailBlast.Status.APPROVED).values_list("id", flat=True)
    )
    skipped_count = queryset.exclude(status=EmailBlast.Status.APPROVED).count()

    for blast_id in approved_blast_ids:
        transaction.on_commit(lambda blast_id=blast_id: send_email_blast.delay(blast_id))

    if approved_blast_ids:
        modeladmin.message_user(
            request,
            f"{len(approved_blast_ids)} email blast"
            f"{'s' if len(approved_blast_ids) != 1 else ''} queued to send.",
        )
    if skipped_count:
        modeladmin.message_user(
            request,
            f"{skipped_count} email blast{'s' if skipped_count != 1 else ''} skipped; "
            "only approved blasts can be sent.",
            level=messages.WARNING,
        )


class EmailBlastTargetNodeInline(admin.TabularInline):
    model = EmailBlastTargetNode
    extra = 0
    fields = (
        "parent",
        "operator",
        "primitive_type",
        "primitive_name",
        "primitive_id",
        "position",
    )


@admin.register(EmailBlastTarget)
class EmailBlastTargetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "created_at",
    )
    search_fields = ("name", "description", "created_by__email")
    inlines = (EmailBlastTargetNodeInline,)


@admin.register(EmailBlastTargetNode)
class EmailBlastTargetNodeAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "target",
        "parent",
        "operator",
        "primitive_type",
        "primitive_name",
        "position",
    )
    list_filter = ("operator", "primitive_type", "created_at")
    search_fields = ("primitive_name", "primitive_id", "target__name")


class EmailBlastDeliveryInline(admin.TabularInline):
    model = EmailBlastDelivery
    extra = 0
    fields = ("email", "profile", "created_at", "sent_at")
    readonly_fields = ("email", "profile", "created_at", "sent_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EmailBlast)
class EmailBlastAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "submitter",
        "reply_to",
        "target_name",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "subject",
        "body",
        "reply_to",
        "submitter__email",
        "submitter__first_name",
        "submitter__last_name",
    )
    readonly_fields = ("submitter", "created_at", "updated_at")
    inlines = (EmailBlastDeliveryInline,)
    actions = (
        mark_as_draft,
        mark_as_submitted,
        mark_as_approved,
        mark_as_rejected,
        send_selected_email_blasts,
    )


@admin.register(EmailBlastDelivery)
class EmailBlastDeliveryAdmin(admin.ModelAdmin):
    list_display = ("email_blast", "email", "profile", "created_at", "sent_at")
    list_filter = ("created_at", "sent_at")
    search_fields = ("email", "email_blast__subject", "profile__user__email")
    readonly_fields = ("email_blast", "profile", "email", "created_at", "sent_at")
