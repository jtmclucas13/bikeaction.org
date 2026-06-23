import io
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase

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
                "DISCORD_OAUTH_CLIENT_ID": "some_client_id",
                "DISCORD_OAUTH_CLIENT_SECRET": "some_client_secret",
            }
            return env_vars.get(key)

        # Mock input to avoid the interactive prompt
        with patch('os.getenv', side_effect=mocked_getenv):
            with patch('builtins.input', return_value='n'):
                stdout = io.StringIO()
                call_command('setup_discord', stdout=stdout)
                output = stdout.getvalue()
                
                self.assertIn("Missing required environment variables", output)
                self.assertIn("NEW_ORGANIZER_REVIEW_DISCORD_GUILD_ID", output)
                self.assertIn("NEIGHBORHOOD_SELECTION_DISCORD_GUILD_ID", output)
                self.assertIn("NEW_PROJECT_REVIEW_DISCORD_GUILD_ID", output)
                self.assertNotIn("DISCORD_OAUTH_CLIENT_ID", output)
                self.assertNotIn("DISCORD_OAUTH_CLIENT_SECRET", output)

    def test_user_aborts_setup(self):
        """
        Verify that entering 'n' during the confirmation prompt aborts the setup.
        """
        def mocked_getenv(key):
            env_vars = {
                "DISCORD_OAUTH_CLIENT_ID": "some_client_id",
                "DISCORD_OAUTH_CLIENT_SECRET": "some_client_secret",
                "NEW_ORGANIZER_REVIEW_DISCORD_GUILD_ID": "123",
                "NEIGHBORHOOD_SELECTION_DISCORD_GUILD_ID": "456",
                "NEW_PROJECT_REVIEW_DISCORD_GUILD_ID": "789",
            }
            return env_vars.get(key)

        with patch('os.getenv', side_effect=mocked_getenv):
            with patch('builtins.input', return_value='n'):
                stdout = io.StringIO()
                call_command('setup_discord', stdout=stdout)
                output = stdout.getvalue()

                self.assertIn("Setup aborted by user.", output)
                self.assertNotIn("Starting Discord setup...", output)

    def test_setup_completes_successfully(self):
        """
        Verify that the setup_discord command completes successfully when all 
        environment variables are present and the user confirms.
        """
        def mocked_getenv(key):
            env_vars = {
                "DISCORD_BOT_TOKEN": "some_bot_token",
                "DISCORD_OAUTH_CLIENT_ID": "some_client_id",
                "DISCORD_OAUTH_CLIENT_SECRET": "some_client_secret",
                "NEW_ORGANIZER_REVIEW_DISCORD_GUILD_ID": "123",
                "NEIGHBORHOOD_SELECTION_DISCORD_GUILD_ID": "456",
                "NEW_PROJECT_REVIEW_DISCORD_GUILD_ID": "789",
            }
            return env_vars.get(key)

        with patch('os.getenv', side_effect=mocked_getenv):
            with patch('builtins.input', return_value='y'):
                stdout = io.StringIO()
                call_command('setup_discord', stdout=stdout)
                output = stdout.getvalue()

                self.assertIn("Environment validation successful.", output)
                self.assertIn("Starting Discord setup...", output)
                self.assertIn("Done!", output)
