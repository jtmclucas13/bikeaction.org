from django.contrib import admin

from emailblasts.models import EmailBlast, EmailBlastTarget, EmailBlastTargetNode


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
