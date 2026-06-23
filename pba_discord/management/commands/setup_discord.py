from django.core.management.base import BaseCommand
import os
import requests
import dotenv

DISCORD_API_BASE_URL = "https://discord.com/api/v10"
    
def get_guild_name(guild_id: str, auth_token: str) -> str | None:
    """
    Fetches the name of a Discord guild.
    """
    try:
        response = requests.get(f"{DISCORD_API_BASE_URL}/guilds/{guild_id}", headers={"Authorization": f"Bot {auth_token}"})
        response.raise_for_status()
        return response.json().get("name")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching guild name: {e}")
        return None

class Command(BaseCommand):
    help = "Sets up the user's Discord environment for development."

    def handle(self, *args, **options):
        dotenv.read_dotenv()

        # Verify environment variables
        required_vars = [
            "DISCORD_BOT_TOKEN",
            "DISCORD_OAUTH_CLIENT_ID",
            "DISCORD_OAUTH_CLIENT_SECRET",
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

        auth_token = os.getenv("DISCORD_BOT_TOKEN")

        organizer_review_guild_name = get_guild_name(os.getenv("NEW_ORGANIZER_REVIEW_DISCORD_GUILD_ID"), auth_token)
        neighborhood_selection_guild_name = get_guild_name(os.getenv("NEIGHBORHOOD_SELECTION_DISCORD_GUILD_ID"), auth_token)
        new_project_review_guild_name = get_guild_name(os.getenv("NEW_PROJECT_REVIEW_DISCORD_GUILD_ID"), auth_token)

        self.stdout.write(self.style.NOTICE(f"Organizer Review Guild: {organizer_review_guild_name}"))
        self.stdout.write(self.style.NOTICE(f"Neighborhood Selection Guild: {neighborhood_selection_guild_name}"))
        self.stdout.write(self.style.NOTICE(f"New Project Review Guild: {new_project_review_guild_name}"))

        if not all([organizer_review_guild_name, neighborhood_selection_guild_name, new_project_review_guild_name]):
            self.stdout.write(self.style.ERROR("Failed to fetch all guild names, guilds may not exist."))
            return

        response = input("Are you sure you want to run the Discord setup? Channels and roles will be created inside of the guilds specified above. (y/N): ")
        
        if response.lower() != 'y':
            self.stdout.write(self.style.WARNING("Setup aborted by user."))
            return

        # --- Actual setup logic goes here ---
        
        self.stdout.write(self.style.SUCCESS("Starting Discord setup..."))
        
        # Placeholder for logic
        self.stdout.write("Done!")

