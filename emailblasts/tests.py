import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Petition, PetitionSignature
from emailblasts.forms import EmailDraftForm
from emailblasts.models import (
    EmailBlast,
    EmailBlastDelivery,
    EmailBlastTarget,
    EmailBlastTargetNode,
)
from emailblasts.tasks import send_email_blast
from emailblasts.views import (
    _email_blast_target_object,
    _email_blast_target_profiles,
    _email_draft_geojson_feature_collection,
    _email_draft_profiles_for_targets,
    _email_draft_target_name,
)
from facets.models import District
from profiles.models import DoNotEmail, Profile


class EmailBlastSendTaskTests(TestCase):
    def create_profile(self, email, first_name="Test", last_name="User"):
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        return Profile.objects.create(user=user)

    def create_all_profiles_blast(self, subject="Test blast"):
        target = EmailBlastTarget.objects.create(
            name="All profiles",
            description="have a PBA account",
        )
        root = EmailBlastTargetNode.objects.create(
            target=target,
            operator=EmailBlastTargetNode.Operator.OR,
        )
        EmailBlastTargetNode.objects.create(
            target=target,
            parent=root,
            primitive_type=EmailBlastTargetNode.TargetType.ALL_PROFILES,
            primitive_name=EmailBlastTargetNode.TargetType.ALL_PROFILES.label,
        )
        return EmailBlast.objects.create(
            subject=subject,
            body="Main message",
            reply_to="organizer@bikeaction.org",
            target=target,
            status=EmailBlast.Status.APPROVED,
        )

    @patch("emailblasts.tasks.send_email_message")
    def test_second_queued_task_does_not_send_duplicate_blast(self, mock_send_email):
        self.create_profile("one@example.com", first_name="One")
        self.create_profile("two@example.com", first_name="Two")
        blast = self.create_all_profiles_blast()

        send_email_blast(blast.id)
        send_email_blast(blast.id)

        self.assertEqual(mock_send_email.call_count, 2)
        self.assertEqual(EmailBlastDelivery.objects.filter(email_blast=blast).count(), 2)
        blast.refresh_from_db()
        self.assertEqual(blast.status, EmailBlast.Status.SENT)

    @patch("emailblasts.tasks.send_email_message")
    def test_suppressed_recipient_is_skipped_case_insensitively(self, mock_send_email):
        self.create_profile("CaseSensitive@example.com")
        DoNotEmail.objects.create(
            email="casesensitive@example.com",
            reason=DoNotEmail.Reason.ACCOUNT_DELETION,
        )
        blast = self.create_all_profiles_blast()

        result = send_email_blast(blast.id)

        mock_send_email.assert_not_called()
        self.assertEqual(EmailBlastDelivery.objects.filter(email_blast=blast).count(), 0)
        self.assertIn("skipped 1 suppressed recipients", result)
        blast.refresh_from_db()
        self.assertEqual(blast.status, EmailBlast.Status.SENT)

    @patch("emailblasts.tasks.send_email_message")
    def test_failed_recipient_send_can_be_retried(self, mock_send_email):
        self.create_profile("retry@example.com")
        blast = self.create_all_profiles_blast()
        mock_send_email.side_effect = [RuntimeError("smtp down"), None]

        with self.assertRaises(RuntimeError):
            send_email_blast(blast.id)

        blast.refresh_from_db()
        self.assertEqual(blast.status, EmailBlast.Status.APPROVED)
        self.assertEqual(EmailBlastDelivery.objects.filter(email_blast=blast).count(), 0)

        send_email_blast(blast.id)

        self.assertEqual(mock_send_email.call_count, 2)
        self.assertEqual(EmailBlastDelivery.objects.filter(email_blast=blast).count(), 1)
        blast.refresh_from_db()
        self.assertEqual(blast.status, EmailBlast.Status.SENT)

    @patch("emailblasts.tasks.send_email_message")
    def test_retry_does_not_email_existing_successful_delivery(self, mock_send_email):
        first_profile = self.create_profile("already@example.com", first_name="Already")
        self.create_profile("new@example.com", first_name="New")
        blast = self.create_all_profiles_blast()
        EmailBlastDelivery.objects.create(
            email_blast=blast,
            profile=first_profile,
            email="already@example.com",
            sent_at=timezone.now(),
        )

        send_email_blast(blast.id)

        self.assertEqual(mock_send_email.call_count, 1)
        self.assertEqual(mock_send_email.call_args.kwargs["to"], ["new@example.com"])
        self.assertEqual(EmailBlastDelivery.objects.filter(email_blast=blast).count(), 2)
        blast.refresh_from_db()
        self.assertEqual(blast.status, EmailBlast.Status.SENT)


class EmailBlastTargetingTests(TestCase):
    def create_profile(self, email, longitude, latitude):
        user = User.objects.create_user(username=email, email=email)
        return Profile.objects.create(user=user, location=Point(longitude, latitude, srid=4326))

    def create_district(self, name, min_x, min_y, max_x, max_y):
        polygon = Polygon(
            (
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y),
                (min_x, min_y),
            ),
            srid=4326,
        )
        return District.objects.create(
            name=name,
            mpoly=MultiPolygon(polygon, srid=4326),
            properties={},
        )

    def target_data(self, target_type, target_id, target_name):
        return {
            "target_type": target_type,
            "target_id": str(target_id),
            "target_name": target_name,
            "target_geojson": None,
        }

    def test_district_targets_can_be_combined_with_or_and_and(self):
        west = self.create_profile("west@example.com", 0.5, 0.5)
        middle = self.create_profile("middle@example.com", 1.5, 1.5)
        east = self.create_profile("east@example.com", 2.5, 2.5)
        district_1 = self.create_district("District 1", 0, 0, 2, 2)
        district_2 = self.create_district("District 2", 1, 1, 3, 3)
        targets = [
            self.target_data(
                EmailBlastTargetNode.TargetType.DISTRICT,
                district_1.pk,
                str(district_1),
            ),
            self.target_data(
                EmailBlastTargetNode.TargetType.DISTRICT,
                district_2.pk,
                str(district_2),
            ),
        ]

        or_profiles = _email_draft_profiles_for_targets(
            targets,
            EmailBlastTargetNode.Operator.OR,
        )
        and_profiles = _email_draft_profiles_for_targets(
            targets,
            EmailBlastTargetNode.Operator.AND,
        )

        self.assertCountEqual(or_profiles, [west, middle, east])
        self.assertCountEqual(and_profiles, [middle])
        self.assertEqual(
            _email_draft_target_name(targets, EmailBlastTargetNode.Operator.AND),
            "District 1 AND District 2",
        )

    def test_all_profiles_target_overrides_other_targets(self):
        first = self.create_profile("first@example.com", 0.5, 0.5)
        second = self.create_profile("second@example.com", 10, 10)
        district = self.create_district("District 1", 0, 0, 2, 2)
        targets = [
            self.target_data(
                EmailBlastTargetNode.TargetType.DISTRICT,
                district.pk,
                str(district),
            ),
            self.target_data(
                EmailBlastTargetNode.TargetType.ALL_PROFILES,
                "",
                EmailBlastTargetNode.TargetType.ALL_PROFILES.label,
            ),
        ]

        profiles = _email_draft_profiles_for_targets(targets)

        self.assertCountEqual(profiles, [first, second])

    def test_petition_target_matches_profiles_by_signer_email(self):
        signer = self.create_profile("signer@example.com", 0, 0)
        self.create_profile("other@example.com", 0, 0)
        petition = Petition.objects.create(title="Safer Streets")
        PetitionSignature.objects.create(
            petition=petition,
            first_name="Signer",
            email="signer@example.com",
        )
        target = self.target_data(
            EmailBlastTargetNode.TargetType.PETITION,
            petition.pk,
            str(petition),
        )

        profiles = _email_draft_profiles_for_targets([target])

        self.assertCountEqual(profiles, [signer])

    def test_persisted_target_evaluates_same_composed_logic(self):
        user = User.objects.create_user(username="organizer", email="organizer@example.com")
        self.create_profile("west@example.com", 0.5, 0.5)
        middle = self.create_profile("middle@example.com", 1.5, 1.5)
        self.create_profile("east@example.com", 2.5, 2.5)
        district_1 = self.create_district("District 1", 0, 0, 2, 2)
        district_2 = self.create_district("District 2", 1, 1, 3, 3)
        targets = [
            self.target_data(
                EmailBlastTargetNode.TargetType.DISTRICT,
                district_1.pk,
                str(district_1),
            ),
            self.target_data(
                EmailBlastTargetNode.TargetType.DISTRICT,
                district_2.pk,
                str(district_2),
            ),
        ]
        persisted_target = _email_blast_target_object(
            "Intersection target",
            "live in both districts",
            EmailBlastTargetNode.Operator.AND,
            targets,
            user,
        )

        profiles = _email_blast_target_profiles(persisted_target)

        self.assertCountEqual(profiles, [middle])

    def test_geojson_feature_collection_linestring_is_accepted_and_rendered_as_polygon(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [-75.21064675141389, 39.952362055357696],
                            [-75.20922893702708, 39.952151222621524],
                            [-75.20944056749815, 39.951348204967275],
                        ],
                    },
                }
            ],
        }
        form = EmailDraftForm()

        cleaned_geojson = form.clean_geojson_boundary(value=json.dumps(geojson))
        feature_collection = _email_draft_geojson_feature_collection(
            [
                {
                    "target_type": EmailBlastTargetNode.TargetType.GEOJSON,
                    "target_id": "",
                    "target_name": "GeoJSON boundary",
                    "target_geojson": cleaned_geojson,
                }
            ]
        )

        self.assertIn('"type": "MultiPolygon"', feature_collection)
