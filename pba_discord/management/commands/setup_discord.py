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

def create_guild_channel(guild_id: str, channel_name: str, auth_token: str, is_category: bool = False, category_id: str | None = None) -> str | None:
    """
    Creates a channel in a Discord guild.
    """
    channel_type = 4 if is_category else 0

    try:
        response = requests.post(
            f"{DISCORD_API_BASE_URL}/guilds/{guild_id}/channels",
            headers={"Authorization": f"Bot {auth_token}", "Content-Type": "application/json"},
            json={"name": channel_name, "type": channel_type, "parent_id": category_id}
        )
        response.raise_for_status()
        return response.json().get("id")
    except requests.exceptions.RequestException as e:
        print(f"Error creating guild channel: {e}")
        return None

class Command(BaseCommand):
    help = "Sets up the user's Discord environment for development."

    def handle(self, *args, **options):
        dotenv.read_dotenv()

        # Verify environment variables
        required_vars = [
            "DISCORD_BOT_TOKEN",
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

        # Fetch names for guilds that will be modified
        organizer_review_guild_name = get_guild_name(os.getenv("NEW_ORGANIZER_REVIEW_DISCORD_GUILD_ID"), auth_token)
        neighborhood_selection_guild_name = get_guild_name(os.getenv("NEIGHBORHOOD_SELECTION_DISCORD_GUILD_ID"), auth_token)
        new_project_review_guild_name = get_guild_name(os.getenv("NEW_PROJECT_REVIEW_DISCORD_GUILD_ID"), auth_token)

        self.stdout.write(f"Organizer Review Guild: {organizer_review_guild_name}")
        self.stdout.write(f"Neighborhood Selection Guild: {neighborhood_selection_guild_name}")
        self.stdout.write(f"New Project Review Guild: {new_project_review_guild_name}")

        if not all([organizer_review_guild_name, neighborhood_selection_guild_name, new_project_review_guild_name]):
            self.stdout.write(self.style.ERROR("Failed to fetch all guild names, guilds may not exist."))
            return

        response = input("Are you sure you want to run the Discord setup? Channels and roles will be created inside of the guilds specified above. (y/N): ")
        
        if response.lower() != 'y':
            self.stdout.write(self.style.WARNING("Setup aborted by user."))
            return
        
        self.stdout.write(self.style.SUCCESS("Starting Discord setup..."))

        # create Projects category and necessary channels
        projects_category_id = create_guild_channel(
            os.getenv("NEW_PROJECT_REVIEW_DISCORD_GUILD_ID"),
            "Projects",
            auth_token,
            is_category=True
        )
        project_review_channel_id = create_guild_channel(
            os.getenv("NEW_PROJECT_REVIEW_DISCORD_GUILD_ID"),
            "Project Review",
            auth_token,
            category_id=projects_category_id
        )
        project_vote_channel_id = create_guild_channel(
            os.getenv("NEW_PROJECT_REVIEW_DISCORD_GUILD_ID"),
            "Project Voting",
            auth_token,
            category_id=projects_category_id
        )
        project_log_channel_id = create_guild_channel(
            os.getenv("NEW_PROJECT_REVIEW_DISCORD_GUILD_ID"),
            "Project Log",
            auth_token,
            category_id=projects_category_id
        )

        # create Organizer role (project reviewer)
        # create Project Lead role
        self.stdout.write(self.style.SUCCESS("Channels and roles successfully created! Add the following to your .env file:"))
        self.stdout.write(f"ACTIVE_PROJECT_CATEGORY_ID={projects_category_id}")
        self.stdout.write(f"NEW_PROJECT_REVIEW_DISCORD_CHANNEL_ID={project_review_channel_id}")
        self.stdout.write(f"NEW_PROJECT_REVIEW_DISCORD_VOTE_CHANNEL_ID={project_vote_channel_id}")
        self.stdout.write(f"PROJECT_LOG_CHANNEL_ID={project_log_channel_id}")
        self.stdout.write(f"NEW_PROJECT_REVIEW_DISCORD_ROLE_MENTION_ID={project_review_channel_id}")
        self.stdout.write(f"NEW_PROJECT_REVIEW_DISCORD_ROLE_VOTE_MENTION_ID={project_review_channel_id}")
        self.stdout.write(f"ACTIVE_PROJECT_LEAD_ROLE_ID={project_review_channel_id}")

        self.stdout.write("Done!")

