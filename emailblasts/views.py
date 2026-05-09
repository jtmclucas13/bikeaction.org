import json
import os
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.gis.geos import GEOSGeometry
from django.db.models.functions import Lower
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from campaigns.models import PetitionSignature
from emailblasts.forms import EmailDraftForm
from emailblasts.models import EmailBlast, EmailBlastTarget, EmailBlastTargetNode
from emailblasts.utils import email_blast_full_body
from pbaabp.email import EMAIL_IMAGE_PATH, render_email_html, template_from_string
from profiles.models import Profile

EMAIL_PREVIEW_CONTEXT = {
    "first_name": "Sam",
    "last_name": "Cyclist",
    "name": "Sam Cyclist",
    "email": "sam@example.com",
    "target_description": "match the selected audience",
}

MUTABLE_EMAIL_BLAST_STATUSES = {
    EmailBlast.Status.DRAFT,
    EmailBlast.Status.SUBMITTED,
    EmailBlast.Status.REJECTED,
}


@login_required
@permission_required("profiles.can_organize", raise_exception=True)
def email_blast_list(request):
    show_all = request.GET.get("scope") == "all"
    blasts = (
        EmailBlast.objects.all() if show_all else EmailBlast.objects.filter(submitter=request.user)
    )

    return render(
        request,
        "emailblasts/email_blast_list.html",
        {
            "show_all": show_all,
            "draft_blasts": _email_blast_list_items(
                blasts.filter(status=EmailBlast.Status.DRAFT).order_by("-updated_at")
            ),
            "submitted_blasts": _email_blast_list_items(
                blasts.filter(
                    status__in=[
                        EmailBlast.Status.SUBMITTED,
                        EmailBlast.Status.APPROVED,
                        EmailBlast.Status.SENDING,
                    ]
                ).order_by("-updated_at")
            ),
            "sent_blasts": _email_blast_list_items(
                blasts.filter(status=EmailBlast.Status.SENT).order_by("-updated_at", "-created_at")
            ),
        },
    )


@login_required
@permission_required("profiles.can_organize", raise_exception=True)
def email_draft(request, draft_id=None):
    draft = None
    if draft_id is not None:
        draft = get_object_or_404(EmailBlast, id=draft_id, submitter=request.user)
    is_read_only = draft is not None and draft.status not in MUTABLE_EMAIL_BLAST_STATUSES

    if request.method == "POST":
        if is_read_only:
            messages.error(request, "Sent or approved email blasts cannot be edited.")
            return redirect("email_draft_edit", draft_id=draft.id)
        form = EmailDraftForm(request.POST)
        if form.is_valid():
            target_queryset, target_name, target_data = _email_draft_target(form)
            target = _email_blast_target_object(
                form.cleaned_data["target_name"],
                form.cleaned_data["target_description"],
                form.cleaned_data["target_operator"],
                target_data,
                request.user,
                existing_target=draft.target if draft else None,
            )
            action = request.POST.get("action")
            status = (
                EmailBlast.Status.DRAFT if action == "save_draft" else EmailBlast.Status.SUBMITTED
            )
            draft = draft or EmailBlast(submitter=request.user)
            draft.subject = form.cleaned_data["subject"]
            draft.body = form.cleaned_data["body"]
            draft.reply_to = form.cleaned_data["reply_to"]
            draft.target = target
            draft.status = status
            draft.save()
            target_count = _email_draft_target_count(target_queryset)
            message = (
                "Draft email blast saved"
                if status == EmailBlast.Status.DRAFT
                else "Draft email blast submitted"
            )
            messages.success(
                request,
                f"{message} for {target_name} ({target_count} targeted profiles).",
            )
            return redirect("email_draft_edit", draft_id=draft.id)
        target_rows = _email_draft_target_rows_from_post(request.POST)
    elif draft is not None:
        form = EmailDraftForm(initial=_email_draft_initial(draft))
        if is_read_only:
            for field_name in (
                "subject",
                "reply_to",
                "target_name",
                "target_description",
                "body",
            ):
                form.fields[field_name].widget.attrs["readonly"] = "readonly"
        target_rows = _email_draft_initial_target_rows(draft)
    else:
        form = EmailDraftForm()
        target_rows = [{"target_type": "", "target_id": "", "target_geojson": ""}]

    return render(
        request,
        "emailblasts/email_draft.html",
        {
            "form": form,
            "draft": draft,
            "is_read_only": is_read_only,
            "preview_context": EMAIL_PREVIEW_CONTEXT,
            "target_choice_groups": form.target_choices,
            "target_rows": target_rows,
            "target_type_choices": form.target_type_choices(),
        },
    )


def _email_draft_initial(draft):
    initial = {
        "subject": draft.subject,
        "body": draft.body,
        "reply_to": draft.reply_to,
        "target_name": draft.target.name if draft.target else "",
        "target_description": draft.target.description if draft.target else "",
        "target_operator": _email_blast_target_root_operator(draft.target),
    }

    return initial


def _email_draft_initial_target_rows(draft):
    targets = _target_primitive_nodes(draft.target) if draft.target else []
    rows = []
    for target in targets:
        rows.append(
            {
                "target_type": target.primitive_type,
                "target_id": target.primitive_id,
                "target_geojson": json.dumps(target.primitive_geojson, indent=2)
                if target.primitive_geojson
                else "",
            }
        )

    return rows or [{"target_type": "", "target_id": "", "target_geojson": ""}]


def _email_draft_target_rows_from_post(post_data):
    rows = []
    indexes = set()
    for key in post_data.keys():
        match = re.match(r"target_type_(\d+)$", key)
        if match:
            indexes.add(int(match.group(1)))

    for index in sorted(indexes):
        rows.append(
            {
                "target_type": post_data.get(f"target_type_{index}", ""),
                "target_id": post_data.get(f"target_value_{index}", ""),
                "target_geojson": post_data.get(f"target_geojson_{index}", ""),
            }
        )

    return rows or [{"target_type": "", "target_id": "", "target_geojson": ""}]


@login_required
@permission_required("profiles.can_organize", raise_exception=True)
def email_draft_preview(request):
    subject = request.POST.get("subject", "")
    body = request.POST.get("body", "")
    target_count = None
    target_name = ""
    target_errors = []
    target_geojson = ""
    preview_errors = []

    if hasattr(settings, "EMAIL_SUBJECT_PREFIX") and subject:
        subject = f"{settings.EMAIL_SUBJECT_PREFIX} {subject}"

    preview_html = ""
    if body:
        target_description = request.POST.get("target_description", "")
        preview_context = {
            **EMAIL_PREVIEW_CONTEXT,
            "target_description": target_description,
        }
        full_body = email_blast_full_body(body, target_description)
        try:
            rendered_body = template_from_string(full_body).render(preview_context)
            preview_html = render_email_html(rendered_body, for_preview=True)
        except Exception as error:
            preview_errors.append(f"Fix the template syntax before submitting: {error}")

    target_queryset, target_name, target_errors, target_geojson = _email_draft_target_from_post(
        request.POST
    )
    target_errors = [*preview_errors, *target_errors]
    if target_queryset is not None:
        target_count = _email_draft_target_count(target_queryset)

    return render(
        request,
        "emailblasts/email_draft_preview.html",
        {
            "preview_subject": subject,
            "preview_html": preview_html,
            "target_count": target_count,
            "has_target_count": target_count is not None,
            "target_name": target_name,
            "target_errors": target_errors,
            "target_geojson": target_geojson,
        },
    )


@login_required
@permission_required("profiles.can_organize", raise_exception=True)
def email_draft_image(request, filename):
    allowed_files = {
        "header-img.png",
        "footer-img.png",
        "twitter-logo-24.png",
        "instagram-logo-24.png",
        "discord-logo-24.png",
    }
    if filename not in allowed_files:
        raise Http404()

    image_path = os.path.join(settings.BASE_DIR, EMAIL_IMAGE_PATH, filename)
    if not os.path.exists(image_path):
        raise Http404()

    return FileResponse(open(image_path, "rb"), content_type="image/png")


def _email_draft_target(form):
    target_data = _email_draft_target_data(form)
    target_operator = form.cleaned_data["target_operator"]
    return (
        _email_draft_profiles_for_targets(target_data, target_operator),
        _email_draft_target_name(target_data, target_operator),
        target_data,
    )


def _email_draft_target_from_post(post_data):
    form = EmailDraftForm(post_data)
    form.full_clean()
    target_errors = list(form.errors.get("__all__", []))
    if target_errors:
        return None, "", target_errors, ""

    try:
        target_queryset, target_name, target_data = _email_draft_target(form)
    except Exception:
        return None, "", ["Selected target was not found."], ""

    return (
        target_queryset,
        target_name,
        [],
        _email_draft_geojson_feature_collection(target_data),
    )


def _email_draft_target_data(form):
    return form.cleaned_data["target_rows"]


def _email_draft_target_name(target_data, operator=EmailBlastTargetNode.Operator.OR):
    if not target_data:
        return "No targets"
    if len(target_data) == 1:
        return target_data[0]["target_name"]
    target_names = [target["target_name"] for target in target_data]
    joiner = " AND " if operator == EmailBlastTargetNode.Operator.AND else " OR "
    summary = joiner.join(target_names[:3])
    if len(target_names) > 3:
        summary = f"{summary}{joiner}..."
    return summary[:255]


def _email_blast_target_object(
    name, description, target_operator, target_data, user, existing_target=None
):
    target = existing_target or EmailBlastTarget(created_by=user)
    target.name = name
    target.description = description
    target.save()
    target.nodes.all().delete()
    root = EmailBlastTargetNode.objects.create(
        target=target,
        operator=target_operator,
        position=0,
        created_by=user,
    )
    for position, primitive in enumerate(target_data):
        EmailBlastTargetNode.objects.create(
            target=target,
            parent=root,
            primitive_type=primitive["target_type"],
            primitive_id=primitive["target_id"],
            primitive_name=primitive["target_name"],
            primitive_geojson=primitive["target_geojson"],
            position=position,
            created_by=user,
        )
    return target


def _email_draft_profiles_for_targets(target_data, operator=EmailBlastTargetNode.Operator.OR):
    if not target_data:
        return Profile.objects.none()
    if any(
        target["target_type"] == EmailBlastTargetNode.TargetType.ALL_PROFILES
        for target in target_data
    ):
        return Profile.objects.all()

    profile_id_sets = []
    for target in target_data:
        profile_id_sets.append(
            set(_email_draft_target_profiles(target).values_list("pk", flat=True))
        )

    if not profile_id_sets:
        profile_ids = set()
    elif operator == EmailBlastTargetNode.Operator.AND:
        profile_ids = set.intersection(*profile_id_sets)
    else:
        profile_ids = set.union(*profile_id_sets)

    return Profile.objects.filter(pk__in=profile_ids)


def _email_draft_target_profiles(target):
    if target["target_type"] == EmailBlastTargetNode.TargetType.ALL_PROFILES:
        return Profile.objects.all()
    if target["target_type"] == EmailBlastTargetNode.TargetType.GEOJSON:
        return _email_draft_geojson_profiles(json.dumps(target["target_geojson"]))
    if target["target_type"] == EmailBlastTargetNode.TargetType.PETITION:
        signer_emails = (
            PetitionSignature.objects.filter(petition_id=target["target_id"])
            .exclude(email__isnull=True)
            .exclude(email="")
            .annotate(email_lower=Lower("email"))
            .values_list("email_lower", flat=True)
        )
        return Profile.objects.annotate(user_email_lower=Lower("user__email")).filter(
            user_email_lower__in=signer_emails
        )
    if target["target_type"] == EmailBlastTargetNode.TargetType.LEGACY:
        return Profile.objects.none()

    field_name = EmailDraftForm.TARGET_FIELD_BY_TYPE.get(target["target_type"])
    model = EmailDraftForm.MODEL_BY_TARGET_FIELD[field_name]
    return model.objects.get(pk=target["target_id"]).contained_profiles.all()


def _email_blast_list_items(blasts):
    items = []
    for blast in blasts.select_related("target").prefetch_related("target__nodes"):
        blast.display_target_name = blast.target.name if blast.target else "No target"
        blast.display_target_count = (
            _email_draft_target_count(_email_blast_target_profiles(blast.target))
            if blast.target
            else 0
        )
        items.append(blast)
    return items


def _email_blast_target_root_operator(target):
    if target is None:
        return EmailBlastTargetNode.Operator.OR
    root = target.nodes.filter(parent__isnull=True).order_by("position", "id").first()
    return root.operator if root and root.operator else EmailBlastTargetNode.Operator.OR


def _target_primitive_nodes(target):
    if target is None:
        return []
    root = target.nodes.filter(parent__isnull=True).order_by("position", "id").first()
    if root and root.operator:
        return list(root.children.order_by("position", "id"))
    return list(target.nodes.filter(operator="").order_by("position", "id"))


def _email_blast_target_profiles(target):
    root = target.nodes.filter(parent__isnull=True).order_by("position", "id").first()
    if root is None:
        return Profile.objects.none()
    profile_ids = _email_blast_target_node_profile_ids(root)
    return Profile.objects.filter(pk__in=profile_ids)


def _email_blast_target_node_profile_ids(node):
    if node.operator:
        child_sets = [
            _email_blast_target_node_profile_ids(child)
            for child in node.children.order_by("position", "id")
        ]
        if not child_sets:
            return set()
        if node.operator == EmailBlastTargetNode.Operator.AND:
            return set.intersection(*child_sets)
        return set.union(*child_sets)

    return set(
        _email_draft_target_profiles(_target_data_from_node(node)).values_list("pk", flat=True)
    )


def _target_data_from_node(node):
    return {
        "target_type": node.primitive_type,
        "target_id": node.primitive_id,
        "target_name": node.primitive_name,
        "target_geojson": node.primitive_geojson,
    }


def _email_draft_geojson_profiles(geojson):
    geometry = _email_draft_geojson_geometry(geojson)
    geom = GEOSGeometry(json.dumps(geometry))
    geom.srid = 4326
    return Profile.objects.filter(location__within=geom)


def _email_draft_geojson_feature_collection(target_data):
    features = []
    for target in target_data:
        if target["target_type"] != EmailBlastTargetNode.TargetType.GEOJSON:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {"name": target["target_name"]},
                "geometry": _email_draft_geojson_geometry(json.dumps(target["target_geojson"])),
            }
        )

    if not features:
        return ""
    return json.dumps({"type": "FeatureCollection", "features": features})


def _email_draft_geojson_geometry(geojson):
    data = json.loads(geojson)
    return EmailDraftForm().geojson_geometry(data)


def _email_draft_target_count(queryset):
    return queryset.exclude(user__email="").values("user__email").distinct().count()
