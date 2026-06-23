from django.core.management.base import BaseCommand
import os
import dotenv

class Command(BaseCommand):
    help = "Sets up the user's Discord environment for development."

    def handle(self, *args, **options):
        dotenv.read_dotenv()

        # Verify environment variables
        required_vars = [
            "DISCORD_CLIENT_ID",
            "DISCORD_CLIENT_SECRET",
            "NEW_ORGANIZER_REVIEW_DISCORD_GUILD_ID",
            "NEIGHBORHOOD_SELECTION_DISCORD_GUILD_ID",
            "NEW_PROJECT_REVIEW_DISCORD_GUILD_ID",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            self.stdout.write(self.style.ERROR(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                "Please set them in your .env file."
            ))
            return

        self.stdout.write(self.style.SUCCESS("Environment validation successful."))

        response = input("Are you sure you want to run the Discord setup? (y/N): ")
        
        if response.lower() != 'y':
            self.stdout.write(self.style.WARNING("Setup aborted by user."))
            return

        # --- Actual setup logic goes here ---
        
        self.stdout.write(self.style.SUCCESS("Starting Discord setup..."))
        
        # Placeholder for logic
        self.stdout.write("Done!")

