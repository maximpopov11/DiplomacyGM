import logging

from discord.ext import commands
import random

from discord.ext.commands import (
    ExtensionNotFound,
    ExtensionNotLoaded,
    ExtensionAlreadyLoaded,
    NoEntryPointError,
    ExtensionFailed,
)

from bot.config import (
    IMPDIP_SERVER_ID,
    IMPDIP_BOT_WIZARD_ROLE,
    ERROR_COLOUR,
    PARTIAL_ERROR_COLOUR,
    IMPDIP_SERVER_BOT_STATUS_CHANNEL_ID,
)
from bot.bot import DiploGM
from bot import perms
from bot.utils import send_message_and_file
from diplomacy.persistence.manager import Manager

logger = logging.getLogger(__name__)
manager = Manager()


class DevelopmentCog(commands.Cog):
    """
    Superuser features primarily used for Development of the bot
    """

    bot: DiploGM

    def __init__(self, bot: DiploGM):
        self.bot = bot

    @commands.command(hidden=True)
    @perms.superuser_only("show the superuser dashboard")
    async def su_dashboard(self, ctx: commands.Context):

        extensions_body = ""
        for extension in self.bot.get_all_extensions():
            if extension in self.bot.extensions.keys():
                extensions_body += "- :white_check_mark: "
            else:
                extensions_body += "- :x: "
            extensions_body += f"{extension}\n"

        cogs_body = ""
        for cog in self.bot.cogs.keys():
            cogs_body += f"- {cog}\n"

        bot_wizards = (
            self.bot.get_guild(IMPDIP_SERVER_ID)
            .get_role(IMPDIP_BOT_WIZARD_ROLE)
            .members
        )
        footer = random.choice(
            [f"Rather upset at {bot_wizard.nick} >:(" for bot_wizard in bot_wizards]
            + [
                f"eolhc keeps {random.choice(['murdering', 'stabbing'])} me",
                f"aahoughton, I don't recognise your union!",
            ]
        )

        await send_message_and_file(
            channel=ctx.channel,
            title=f"DiplomacyGM Dashboard",
            fields=[("Extensions", extensions_body), ("Loaded Cogs", cogs_body)],
            footer_content=footer,
        )

    @commands.command(hidden=True)
    @perms.superuser_only("unloaded extension")
    async def extension_unload(self, ctx: commands.Context, extension: str):
        try:
            await self.bot.unload_extension(extension)
        except ExtensionNotFound:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension was not found: {extension}",
                embed_colour=ERROR_COLOUR,
            )
            return
        except ExtensionNotLoaded:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension was not loaded: {extension}",
                embed_colour=PARTIAL_ERROR_COLOUR,
            )
            return
        await send_message_and_file(
            channel=ctx.channel, title=f"Unloaded Extension {extension}"
        )

    @commands.command(hidden=True)
    @perms.superuser_only("load extension")
    async def extension_load(self, ctx: commands.Context, extension: str):
        try:
            await self.bot.load_extension(extension)
        except ExtensionNotFound:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension was not found: {extension}",
                embed_colour=ERROR_COLOUR,
            )
            return
        except ExtensionAlreadyLoaded:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension was already loaded: {extension}",
                embed_colour=PARTIAL_ERROR_COLOUR,
            )
            return
        except NoEntryPointError:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension has no setup function: {extension}",
                embed_colour=ERROR_COLOUR,
            )
            return
        except ExtensionFailed:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension failed to load: {extension}",
                embed_colour=ERROR_COLOUR,
            )
            return
        await send_message_and_file(
            channel=ctx.channel, title=f"Loaded Extension {extension}"
        )

    @commands.command(hidden=True)
    @perms.superuser_only("reload extension")
    async def extension_reload(self, ctx: commands.Context, extension: str):
        try:
            await self.bot.unload_extension(extension)
        except ExtensionNotFound:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension was not found: {extension}",
                embed_colour=ERROR_COLOUR,
            )
            return
        except ExtensionNotLoaded:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension was not loaded: {extension}",
                embed_colour=PARTIAL_ERROR_COLOUR,
            )
            return
        try:
            await self.bot.load_extension(extension)
        except ExtensionNotFound:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension was not found: {extension}",
                embed_colour=ERROR_COLOUR,
            )
            return
        except ExtensionAlreadyLoaded:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension was already loaded: {extension}",
                embed_colour=PARTIAL_ERROR_COLOUR,
            )
            return
        except NoEntryPointError:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension has no setup function: {extension}",
                embed_colour=ERROR_COLOUR,
            )
            return
        except ExtensionFailed:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Extension failed to load: {extension}",
                embed_colour=ERROR_COLOUR,
            )
            return
        await send_message_and_file(
            channel=ctx.channel, title=f"Reloaded Extension {extension}"
        )

    @commands.command(hidden=True)
    @perms.superuser_only("shutdown the bot")
    async def shutdown_the_bot_yes_i_want_to_do_this(self, ctx: commands.Context):
        await send_message_and_file(
            channel=ctx.channel, title=f"Why?", message=f"Shutting down"
        )
        channel = self.bot.get_channel(IMPDIP_SERVER_BOT_STATUS_CHANNEL_ID)
        if channel:
            await channel.send(f"{ctx.author.mention} stabbed me")
        await self.bot.close()


async def setup(bot: DiploGM):
    cog = DevelopmentCog(bot)
    await bot.add_cog(cog)


async def teardown(bot: DiploGM):
    pass
