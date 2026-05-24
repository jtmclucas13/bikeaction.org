from django.test import SimpleTestCase, override_settings

from projects.tasks import (
    build_project_approved_channel_message,
    build_project_lead_cheat_sheet_dm_message,
)


class ProjectApprovalMessageTests(SimpleTestCase):
    @override_settings(PROJECT_LEAD_CHEAT_SHEET_URL="https://example.com/cheat-sheet")
    def test_approved_channel_message_includes_project_lead_cheat_sheet(self):
        message = build_project_approved_channel_message(
            guild_id="guild-123",
            application_thread_id="thread-456",
            project_lead_mention="<@789>",
        )

        self.assertIn("✅ This project has been approved!", message)
        self.assertIn("https://discord.com/channels/guild-123/thread-456", message)
        self.assertIn("Project Lead: <@789>.", message)
        self.assertIn(
            "ℹ️ For the basics on PBA resources, reimbursements, promotion, events, "
            "volunteer support, and wrapping up your project, read the "
            "[Project Lead Cheat Sheet](<https://example.com/cheat-sheet>).",
            message,
        )

    @override_settings(PROJECT_LEAD_CHEAT_SHEET_URL="https://example.com/cheat-sheet")
    def test_approved_channel_message_includes_project_mentor_when_present(self):
        message = build_project_approved_channel_message(
            guild_id="guild-123",
            application_thread_id="thread-456",
            project_lead_mention="<@789>",
            mentor_mention="<@101>",
        )

        self.assertIn(
            "<@101> has volunteered to support this project by answering any questions.",
            message,
        )

    @override_settings(PROJECT_LEAD_CHEAT_SHEET_URL=None)
    def test_approved_channel_message_omits_cheat_sheet_when_url_is_not_configured(self):
        message = build_project_approved_channel_message(
            guild_id="guild-123",
            application_thread_id="thread-456",
            project_lead_mention="<@789>",
        )

        self.assertIn("✅ This project has been approved!", message)
        self.assertIn("Project Lead: <@789>.", message)
        self.assertNotIn("Project Lead Cheat Sheet", message)
        self.assertNotIn("For the basics on PBA resources", message)

    @override_settings(PROJECT_LEAD_CHEAT_SHEET_URL="https://example.com/cheat-sheet")
    def test_project_lead_dm_message_includes_cheat_sheet(self):
        message = build_project_lead_cheat_sheet_dm_message(
            project_name="Better Bike Lanes",
        )

        self.assertIn('✅ Your project "Better Bike Lanes" has been approved!', message)
        self.assertNotIn("discord.com/channels", message)
        self.assertIn(
            "ℹ️ For the basics on PBA resources, reimbursements, promotion, events, "
            "volunteer support, and wrapping up your project, read the "
            "[Project Lead Cheat Sheet](<https://example.com/cheat-sheet>).",
            message,
        )

    @override_settings(PROJECT_LEAD_CHEAT_SHEET_URL=None)
    def test_project_lead_dm_message_omits_cheat_sheet_when_url_is_not_configured(self):
        message = build_project_lead_cheat_sheet_dm_message(
            project_name="Better Bike Lanes",
        )

        self.assertIn('✅ Your project "Better Bike Lanes" has been approved!', message)
        self.assertNotIn("Project Lead Cheat Sheet", message)
        self.assertNotIn("For the basics on PBA resources", message)

    @override_settings(PROJECT_LEAD_CHEAT_SHEET_URL="https://example.com/cheat-sheet")
    def test_project_lead_dm_message_includes_project_mentor_when_present(self):
        message = build_project_lead_cheat_sheet_dm_message(
            project_name="Better Bike Lanes",
            mentor_mention="<@101>",
        )

        self.assertIn(
            "<@101> has volunteered to support this project by answering any questions.",
            message,
        )
