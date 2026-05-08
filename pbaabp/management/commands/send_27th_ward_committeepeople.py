from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from facets.models import Division
from pbaabp.email import send_email_message

EMAIL_TEMPLATE = "27th-ward-committeepeople"
FROM_EMAIL = "Philly Bike Action <noreply@bikeaction.org>"
REPLY_TO = ["gabriel@bikeaction.org"]
SENT = []

VOTE_SUBJECT = "VOTE MAY 19: Elect bike-friendly Committeepeople for the 27th Ward!"
ACTION_SUBJECT = "ACTION: Elect bike-friendly Committeepeople for the 27th Ward!"

DIVISION_CONFIGS = {
    1: {
        "subject": VOTE_SUBJECT,
        "division_label": "1st",
        "variant": "standard",
        "champion_label": "champion",
        "candidate_word": "candidate",
        "candidate_names": "Noah M. Kocher",
        "candidates": [
            {
                "name": "Noah Kocher",
                "note": (
                    "(see his 5th Square candidate bio "
                    "[here](https://www.5thsq.org/2026_committeeperson_profiles#noah-m-kocher))"
                ),
            },
        ],
    },
    6: {
        "subject": ACTION_SUBJECT,
        "division_label": "6th",
        "variant": "vacancy",
        "can_run": True,
    },
    8: {
        "subject": ACTION_SUBJECT,
        "division_label": "8th",
        "variant": "vacancy",
        "can_run": True,
    },
    9: {
        "subject": VOTE_SUBJECT,
        "division_label": "9th",
        "variant": "write_in",
        "candidate_names": "Owen Sahnow",
        "candidates": [{"name": "Owen Sahnow"}],
    },
    16: {
        "subject": ACTION_SUBJECT,
        "division_label": "16th",
        "variant": "vacancy",
        "can_run": False,
    },
    17: {
        "subject": VOTE_SUBJECT,
        "division_label": "17th",
        "variant": "opposition",
        "candidate_names": "Joe Russo and Marissa Johnson Valenzuela",
        "candidates": [
            {"name": "Joe Russo"},
            {"name": "Marissa Johnson Valenzuela"},
        ],
    },
    22: {
        "subject": VOTE_SUBJECT,
        "division_label": "22nd",
        "variant": "write_in",
        "candidate_names": "Arlo Strauss",
        "candidates": [{"name": "Arlo Strauss"}],
    },
    23: {
        "subject": VOTE_SUBJECT,
        "division_label": "23rd",
        "variant": "standard",
        "champion_label": "champions",
        "candidate_word": "candidates",
        "candidate_names": "Ben Moss-Horwitz and Tammer Ali Ibrahim",
        "candidates": [
            {"name": "Ben Moss-Horwitz", "note": "(a longtime PBA member)"},
            {"name": "Tammer Ali Ibrahim"},
        ],
    },
}


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--division",
            type=int,
            choices=sorted(DIVISION_CONFIGS),
            help="Send only one 27th Ward division email",
        )

    def handle(self, *args, **options):
        settings.EMAIL_SUBJECT_PREFIX = ""
        division_numbers = (
            [options["division"]] if options["division"] else sorted(DIVISION_CONFIGS)
        )
        division_sent_counts = {}

        for division_number in division_numbers:
            config = DIVISION_CONFIGS[division_number]
            division = Division.objects.filter(name=f"Ward 27 Division {division_number}").first()

            if division is None:
                raise CommandError(f"Ward 27 Division {division_number} was not found")

            self.stdout.write(f"Sending {config['division_label']} Division email")
            division_sent_counts[division.name] = 0

            for profile in division.contained_profiles.all():
                email = profile.user.email.lower()

                if email not in SENT:
                    send_email_message(
                        EMAIL_TEMPLATE,
                        FROM_EMAIL,
                        [profile.user.email],
                        {
                            "first_name": profile.user.first_name,
                            **config,
                        },
                        reply_to=REPLY_TO,
                    )
                    SENT.append(email)
                    division_sent_counts[division.name] += 1
                    self.stdout.write(f"Sent to {profile.user.email}")
                else:
                    self.stdout.write(f"Skipping duplicate: {profile.user.email}")

        self.stdout.write("Sent by division:")
        for division_name, sent_count in division_sent_counts.items():
            self.stdout.write(f"{division_name}: {sent_count}")

        self.stdout.write(self.style.SUCCESS(f"Sent {len(SENT)} emails total"))
