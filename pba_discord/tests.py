import io
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase, override_settings


@override_settings(DEBUG=True)
class SetupDiscordCommandTest(TestCase):
    def test_missing_env_vars_prints_error(self):
        """
        Verify that the setup_discord command prints an error message
        when required environment variables are missing.
        """

        # Mock os.getenv to return values for some keys and None for others
        def mocked_getenv(key):
            env_vars = {
                "DISCORD_BOT_TOKEN": "some_bot_token",
            }
            return env_vars.get(key)

        # Mock input to avoid the interactive prompt
        with patch("os.getenv", side_effect=mocked_getenv):
            with patch("builtins.input", return_value="n"):
                stdout = io.StringIO()
                call_command("setup_discord", stdout=stdout)
                output = stdout.getvalue()

                self.assertIn("Missing required environment variables", output)
                self.assertIn("DISCORD_GUILD_ID", output)

    @patch("requests.get")
    def test_user_aborts_setup(self, mock_get):
        """
        Verify that entering 'n' during the confirmation prompt aborts the setup.
        """

        def mocked_getenv(key):
            env_vars = {
                "DISCORD_BOT_TOKEN": "some_bot_token",
                "DISCORD_GUILD_ID": "456",
            }
            return env_vars.get(key)

        # The first call is get_guild_name, the rest are get_guild_channels and get_guild_roles
        mock_get.return_value.json.side_effect = [
            {"name": "Test Guild"},  # guild_name
            [],  # existing_channels (Projects category)
            [],  # existing_channels (Project Review)
            [],  # existing_channels (Project Voting)
            [],  # existing_channels (Project Log)
            [],  # existing_roles (Organizer)
            [],  # existing_roles (Project Lead)
        ]
        mock_get.return_value.raise_for_status.return_value = None

        with patch("os.getenv", side_effect=mocked_getenv):
            with patch("builtins.input", return_value="n"):
                stdout = io.StringIO()
                call_command("setup_discord", stdout=stdout)
                output = stdout.getvalue()

                self.assertIn("Setup aborted by user.", output)
                self.assertNotIn("Starting Discord setup...", output)

    @patch("requests.get")
    @patch("requests.post")
    def test_setup_completes_successfully(self, mock_post, mock_get):
        """
        Verify that the setup_discord command completes successfully when all
        environment variables are present and the user confirms.
        """

        def mocked_getenv(key):
            env_vars = {
                "DISCORD_BOT_TOKEN": "some_bot_token",
                "DISCORD_GUILD_ID": "456",
            }
            return env_vars.get(key)

        mock_channel_id = "new_channel_id"
        mock_get.return_value.json.side_effect = [
            {"name": "Test Guild"},  # guild_name
            [],  # existing_channels (Projects category)
            [],  # existing_channels (Project Review)
            [],  # existing_channels (Project Voting)
            [],  # existing_channels (Project Log)
            [],  # existing_roles (Organizer)
            [],  # existing_roles (Project Lead)
        ]
        mock_get.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"id": mock_channel_id}
        mock_post.return_value.raise_for_status.return_value = None

        with patch("os.getenv", side_effect=mocked_getenv):
            with patch("builtins.input", return_value="y"):
                stdout = io.StringIO()
                call_command("setup_discord", stdout=stdout)
                output = stdout.getvalue()

                self.assertIn("Environment validation successful.", output)
                self.assertIn("Starting Discord setup...", output)
                self.assertIn(
                    "Channels and roles successfully created! Add the following to your .env file:",
                    output,
                )
                self.assertIn(f"ACTIVE_PROJECT_CATEGORY_ID={mock_channel_id}", output)
                self.assertIn(f"NEW_PROJECT_REVIEW_DISCORD_CHANNEL_ID={mock_channel_id}", output)
                self.assertIn(
                    f"NEW_PROJECT_REVIEW_DISCORD_VOTE_CHANNEL_ID={mock_channel_id}", output
                )
                self.assertIn(f"PROJECT_LOG_CHANNEL_ID={mock_channel_id}", output)
                self.assertIn(
                    f"NEW_PROJECT_REVIEW_DISCORD_ROLE_MENTION_ID={mock_channel_id}", output
                )
                self.assertIn(
                    f"NEW_PROJECT_REVIEW_DISCORD_ROLE_VOTE_MENTION_ID={mock_channel_id}", output
                )
                self.assertIn(f"ACTIVE_PROJECT_LEAD_ROLE_ID={mock_channel_id}", output)
                self.assertIn("Done!", output)
