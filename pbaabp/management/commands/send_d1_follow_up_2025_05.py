from django.core.management.base import BaseCommand

from events.models import EventSignIn, ScheduledEvent
from pbaabp.email import send_email_message

EVENT_ID = "b10d53cf-913f-42eb-86a9-25f3c39358be"
EMAIL_TEMPLATE = "d1-follow-up-2025-05"
SENT = []


class Command(BaseCommand):
    def handle(self, *args, **options):
        event = ScheduledEvent.objects.get(id=EVENT_ID)
        sign_ins = EventSignIn.objects.filter(event=event)

        for sign_in in sign_ins:
            email = sign_in.email.lower()

            if email not in SENT:
                send_email_message(
                    EMAIL_TEMPLATE,
                    "Philly Bike Action <noreply@bikeaction.org>",
                    [sign_in.email],
                    {
                        "first_name": sign_in.first_name,
                        "last_name": sign_in.last_name,
                    },
                    reply_to=["district1@bikeaction.org"],
                )
                SENT.append(email)
                self.stdout.write(f"Sent to {sign_in.email}")
            else:
                self.stdout.write(f"Skipping duplicate: {sign_in.email}")

        self.stdout.write(self.style.SUCCESS(f"Sent {len(SENT)} emails total"))
