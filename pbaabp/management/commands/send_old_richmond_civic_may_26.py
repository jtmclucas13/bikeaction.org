from django.conf import settings
from django.core.management.base import BaseCommand

from facets.models import RegisteredCommunityOrganization
from pbaabp.email import send_email_message

EMAIL_TEMPLATE = "old-richmond-civic-may-26"
RCO_NAMES = [
    "Olde Richmond Civic Association",
    "South Port Richmond Civic Association",
]
SENT = []


class Command(BaseCommand):
    def handle(self, *args, **options):
        settings.EMAIL_SUBJECT_PREFIX = ""
        rcos = RegisteredCommunityOrganization.objects.filter(name__in=RCO_NAMES)

        for rco in rcos:
            self.stdout.write(f"Sending to profiles in {rco.name}")

            for profile in rco.contained_profiles.all():
                email = profile.user.email.lower()

                if email not in SENT:
                    send_email_message(
                        EMAIL_TEMPLATE,
                        "Philly Bike Action <noreply@bikeaction.org>",
                        [profile.user.email],
                        {"first_name": profile.user.first_name},
                        reply_to=["district1@bikeaction.org"],
                    )
                    SENT.append(email)
                    self.stdout.write(f"Sent to {profile.user.email}")
                else:
                    self.stdout.write(f"Skipping duplicate: {profile.user.email}")

        self.stdout.write(self.style.SUCCESS(f"Sent {len(SENT)} emails total"))
