import re

from asgiref.sync import sync_to_async
from django.conf import settings
from django.urls import reverse
from interactions import (
    Button,
    ButtonStyle,
    Embed,
    Extension,
    OptionType,
    SlashContext,
    component_callback,
    listen,
    slash_command,
    slash_option,
    spread_to_rows,
)
from interactions.api.events import Startup

EMBED_TITLE = "Neighborhood Selection"
EMBED_DESCRIPTION = (
    "This is the Neighborhood Selection Panel. "
    "Click on each neighborhood button to enter its chat channel. "
    "There is no limit to the amount of neighborhood chat channels you can join."
    "\n"
    "If you don’t see your neighborhood here and want to start the channel, "
    "use the `/neighborhood` command to request a new one!"
)


class NeighborhoodSelection(Extension):
    SELECTION_CHANNEL = settings.NEIGHBORHOOD_SELECTION_DISCORD_CHANNEL_ID

    def __init__(self, bot):
        self.bot = bot
        self.components = None
        self.NEIGHBORHOODS = {}

    @slash_command(name="neighborhood", description="Request a neighborhood channel")
    @slash_option(
        name="neighborhood_name",
        description="The name of the neighborhood you are requesting",
        required=True,
        opt_type=OptionType.STRING,
    )
    async def request_neighborhood(self, ctx: SlashContext, neighborhood_name: str):
        from neighborhood_selection.models import Neighborhood

        neighborhood, _ = await Neighborhood.objects.aget_or_create(
            defaults={"name": neighborhood_name},
            name__iexact=neighborhood_name,
        )
        if neighborhood.approved:
            await ctx.send(
                (
                    f"{neighborhood.name} channel already exists, "
                    "use the button in #neighborhood-selection to join!"
                ),
                ephemeral=True,
            )
            return
        neighborhood.requests += 1
        await neighborhood.asave()
        msg = f"Neighborhood request for {neighborhood_name} recorded!"
        if neighborhood.requests > 1:
            msg += f" You and {neighborhood.requests - 1} users are waiting for it to be approved."
        if settings.NEIGHBORHOOD_SELECTION_NOTIFICATION_DISCORD_CHANNEL_ID:
            approval_path = reverse(
                "admin:%s_%s_change"
                % (neighborhood._meta.app_label, neighborhood._meta.model_name),
                args=[neighborhood.id],
            )
            approval_url = f"{settings.SITE_URL}{approval_path}"
            await self.bot.get_channel(
                settings.NEIGHBORHOOD_SELECTION_NOTIFICATION_DISCORD_CHANNEL_ID
            ).send(
                (
                    f"Neighborhood request for `{neighborhood.name}` received! "
                    f"A total of {neighborhood.requests} people have requested it! "
                    "\n"
                    f"Go to {approval_url} when you're ready to approve it."
                )
            )
        await ctx.send(msg, ephemeral=True)

    @staticmethod
    async def update_buttons(bot, selection_channel, components):
        from neighborhood_selection.models import Neighborhood

        if not selection_channel:
            print("No selection channel, bailing!")

        guild = await bot.fetch_guild(settings.DISCORD_GUILD_ID)
        BUTTONS = []
        for neighborhood in await sync_to_async(list)(
            Neighborhood.objects.filter(approved=True).order_by("-featured", "name")
        ):
            role = await guild.fetch_role(neighborhood.discord_role_id, force=True)
            label = neighborhood.name
            if len(role.members) == 1:
                label = f"{neighborhood.name} ({len(role.members)} 👤)"
            elif len(role.members) > 1:
                label = f"{neighborhood.name} ({len(role.members)} 👥)"
            BUTTONS.append(
                Button(
                    style=ButtonStyle.PRIMARY if neighborhood.featured else ButtonStyle.SECONDARY,
                    label=label,
                    custom_id=f"neighborhood_selection_{neighborhood.id}",
                )
            )
        BUTTON_LIMIT = 20
        button_groups = [
            spread_to_rows(*BUTTONS[i : (i + BUTTON_LIMIT)], max_in_row=4)  # noqa: E203
            for i in range(0, len(BUTTONS), BUTTON_LIMIT)
        ]

        embed = Embed(
            title=EMBED_TITLE,
            description=EMBED_DESCRIPTION,
        )
        channel = await bot.fetch_channel(selection_channel)
        intro_exists = False
        button_groups_i = iter(button_groups)
        button_groups_exist = [False for bg in button_groups]
        bg_i = 0
        history = await channel.history().flatten()
        for message in reversed(history):
            if len(message.embeds) == 1 and message.embeds[0].title == EMBED_TITLE:
                print("updating embed...")
                await message.edit(content=None, embeds=[embed])
                intro_exists = True
            elif len(message.embeds) == 0 and len(message.components) > 0:
                await message.edit(content=None, components=next(button_groups_i))
                button_groups_exist[bg_i] = True
                bg_i += 1
        if not intro_exists:
            await bot.get_channel(selection_channel).send(None, embeds=[embed])
        for i, button_group in enumerate(button_groups):
            if not button_groups_exist[i]:
                await bot.get_channel(selection_channel).send(None, components=button_groups[i])

    @listen(Startup)
    async def startup(self):
        await self.update_buttons(self.bot, self.SELECTION_CHANNEL, self.components)

    BUTTON_ID_REGEX = re.compile(r"neighborhood_selection_(.*)")

    @component_callback(BUTTON_ID_REGEX)
    async def callback(self, ctx):
        from neighborhood_selection.models import Neighborhood

        neighborhood_id = ctx.custom_id.replace("neighborhood_selection_", "")
        neighborhood = await Neighborhood.objects.filter(id=neighborhood_id).afirst()
        if neighborhood is None:
            await ctx.send("No neighborhood found!", ephemeral=True)
            return

        guild = await self.bot.fetch_guild(settings.DISCORD_GUILD_ID)
        role = await guild.fetch_role(neighborhood.discord_role_id)
        if role not in ctx.member.roles:
            await ctx.member.add_role(neighborhood.discord_role_id)
            await ctx.send(f"Added {neighborhood.name} role!", ephemeral=True)
            await self.update_buttons(self.bot, self.SELECTION_CHANNEL, self.components)
            return
        else:
            await ctx.member.remove_role(neighborhood.discord_role_id)
            await ctx.send(f"Removed {neighborhood.name} role.", ephemeral=True)
            await self.update_buttons(self.bot, self.SELECTION_CHANNEL, self.components)
            return


def setup(bot):
    NeighborhoodSelection(bot)
