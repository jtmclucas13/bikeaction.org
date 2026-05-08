from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand

from pbaabp.email import send_email_message
from profiles.models import Profile

EMAIL_TEMPLATE = "germantown-ave-bike-lane"
SENT = []

GEOJSON = """
{
  "type": "Polygon",
  "coordinates": [
    [
      [
        -75.14151627153358,
        39.96068044686089
      ],
      [
        -75.13455213681014,
        39.968736062495935
      ],
      [
        -75.13282182686243,
        39.98161007091221
      ],
      [
        -75.1374921924853,
        39.985549502728475
      ],
      [
        -75.14463509907446,
        39.98004627903779
      ],
      [
        -75.14989174257703,
        39.9704391423692
      ],
      [
        -75.14689012867717,
        39.96327795432552
      ],
      [
        -75.14151627153358,
        39.96068044686089
      ]
    ]
  ]
}
"""

geom = GEOSGeometry(GEOJSON)
geom.srid = 4326


class Command(BaseCommand):
    def handle(self, *args, **options):
        settings.EMAIL_SUBJECT_PREFIX = ""
        profiles = Profile.objects.filter(location__within=geom)

        for profile in profiles:
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
