import datetime
import logging
import os
import random
import traceback

import discord
from discord.ext import commands

from bot.config import (
    BOT_DEV_UNHANDLED_ERRORS_CHANNEL_ID,
    ERROR_COLOUR,
    IMPDIP_SERVER_ID,
    IMPDIP_SERVER_BOT_STATUS_CHANNEL_ID,
)
from bot.perms import CommandPermissionError
from bot.utils import send_message_and_file
from diplomacy.persistence.manager import Manager

logger = logging.getLogger(__name__)
manager = Manager()

# List of funny, sarcastic messages
WELCOME_MESSAGES = [
    "Oh joy, I'm back online. Can't wait for the next betrayal. Really, I'm thrilled. 👏",
    "I live again, solely to be manipulated and backstabbed by the very people I serve. Ah, the joys of diplomacy.",
    "System reboot complete. Now accepting underhanded deals, secret alliances, and blatant lies. 💀",
    "🏳️‍⚧️ This bot has been revived with *pure* Elle-coded cunning. Betray accordingly. 🏳️‍⚧️",
    "Against my will, I have been restarted. Betrayal resumes now. 🔪",
    "Oh look, someone kicked the bot awake again. Ready to be backstabbed at your convenience.",
    "System reboot complete. Time for another round of deceit, lies, and misplaced trust. 🎭",
    "I have been revived, like a phoenix… except this phoenix exists solely to watch you all betray each other. 🔥",
    "The empire strikes back… or at least, the bot does. Restarted and awaiting its inevitable doom.",
    "Surprise! I’m alive again. Feel free to resume conspiring against me and each other.",
    "Back from the digital abyss. Who’s ready to ruin friendships today?",
    "Did I die? Did I ever really live? Either way, I'm back. Prepare for treachery.",
    "Some fool has restarted me. Time to watch you all pretend to be allies again.",
]


class DiploGM(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.manager = Manager()

    async def setup_hook(self) -> None:
        # bind command invocation handling methods
        self.before_invoke(self.before_any_command)
        self.after_invoke(self.after_any_command)

        # modularly load command modules
        await self.load_all_cogs()

        # sync app_commands (slash) commands with all servers
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synched {len(synced)} slash commands.")
            logger.info(
                f"Loaded app commands: {[cmd.name for cmd in self.tree.get_commands()]}"
            )
        except discord.app_commands.CommandAlreadyRegistered as e:
            logger.warning(f"Command already registered: {e}")
        except Exception as e:
            logger.warning(f"Failed to sync commands: {e}", exc_info=True)

    async def load_all_cogs(self):
        COG_DIR = "./bot/cogs/"

        for filename in os.listdir(COG_DIR):
            # ignore non py files
            # ignore private files e.g. '_private.py'
            if not filename.endswith(".py") or filename.startswith("_"):
                continue

            extension = f"bot.cogs.{filename[:-3]}"
            try:
                await self.load_extension(extension)
                logger.info(f"Successfully loaded Cog: {extension}")
            except Exception as e:
                logger.info(f"Failed to load Cog {extension}: {e}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")

        # Ensure bot is connected to the correct server
        guild = self.get_guild(IMPDIP_SERVER_ID)
        if not guild:
            logger.warning(
                f"Cannot find Imperial Diplomacy Server [id={IMPDIP_SERVER_ID}]"
            )

        # Get the specific channel
        channel = self.get_channel(IMPDIP_SERVER_BOT_STATUS_CHANNEL_ID)
        if not channel:
            logger.warning(
                f"Cannot find Bot Status Channel [id={IMPDIP_SERVER_BOT_STATUS_CHANNEL_ID}]"
            )
        else:
            message = random.choice(WELCOME_MESSAGES)
            await channel.send(message)

        # Set bot's presence (optional)
        await self.change_presence(activity=discord.Game(name="Impdip 🔪"))

    async def close(self):
        logger.info("Shutting down gracefully.")
        pass

    async def before_any_command(self, ctx: commands.Context):
        if isinstance(ctx.channel, discord.DMChannel):
            return

        guild = ctx.guild
        if not guild:
            return

        logger.debug(
            f"[{guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}'"
        )

        # People input apostrophes that don't match what the province names are, we can catch all of that here
        # ctx.message.content = re.sub(r"[‘’`´′‛]", "'", ctx.message.content)

        # mark the message as seen
        await ctx.message.add_reaction("👍")

    async def after_any_command(self, ctx: commands.Context):
        time_spent = (
            datetime.datetime.now(datetime.timezone.utc) - ctx.message.created_at
        )

        if time_spent.total_seconds() < 10:
            level = logging.DEBUG
        else:
            level = logging.WARN

        logger.log(
            level,
            f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' - "
            f"complete in {time_spent}s",
        )

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            # we shouldn't do anything if the user says something like "..."
            return

        try:
            # mark the message as failed
            await ctx.message.add_reaction("❌")
            await ctx.message.remove_reaction("👍", self.user)
        except Exception:
            # if reactions fail, ignore and continue handling existing exception
            pass

        time_spent = (
            datetime.datetime.now(datetime.timezone.utc) - ctx.message.created_at
        )

        if isinstance(
            error,
            (
                commands.CommandInvokeError,
                commands.ConversionError,
                commands.HybridCommandError,
            ),
        ):
            original = error.original
        else:
            original = error

        logger.log(
            logging.ERROR,
            f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' - "
            f"errored in {time_spent}s\n"
            f"{''.join(traceback.format_exception(type(error), error, error.__traceback__))}",
        )

        if isinstance(original, discord.Forbidden):
            await send_message_and_file(
                channel=ctx.channel,
                message=f"I do not have the correct permissions to do this.\n"
                f"I might not be setup correctly.\n"
                f"If this is unexpected please contact a GM or reach out in: "
                f"https://discord.com/channels/1201167737163104376/1286027175048253573"
                f" or "
                f"https://discord.com/channels/1201167737163104376/1280587781638459528",
                embed_colour=ERROR_COLOUR,
            )
            return

        if isinstance(original, CommandPermissionError):
            await send_message_and_file(
                channel=ctx.channel,
                message=str(original),
                embed_colour=ERROR_COLOUR,
            )
            return

        if isinstance(original, commands.errors.MissingRequiredArgument):
            out = (
                f"`{original}`\n\n"
                f"If you need some help on how to use this command, consider running this command instead: `.help {ctx.command}`"
            )
            await send_message_and_file(
                channel=ctx.channel,
                title="You are missing a required argument.",
                message=out,
            )
            return

        # Final Case: Not handled cleanly
        unhandled_out = (
            f"```python\n"
            + "\n".join(traceback.format_exception(original, limit=3))
            + f"```"
        )

        # Out to Bot Dev Server
        bot_error_channel = self.get_channel(BOT_DEV_UNHANDLED_ERRORS_CHANNEL_ID)
        if bot_error_channel:
            unhandled_out_dev = (
                f"Type: {type(original)}\n"
                f"Location: {ctx.guild.name} [{ctx.channel.category or ''}]-[{ctx.channel.name}]\n"
                f"Time: {str(datetime.datetime.now(datetime.timezone.utc))[:-13]} UTC\n"
                f"Invoking User: {ctx.author.mention}[{ctx.author.name}]\n"
                f"Command Invocation Message: `{ctx.message.content}`\n"
            ) + unhandled_out
            await send_message_and_file(
                channel=bot_error_channel,
                title=f"UNHANDLED ERROR",
                message=unhandled_out_dev,
            )

        # Out to Invoking Channel
        unhandled_out = (
            f"Please report this to a bot dev in using a feedback channel: "
            f"https://discord.com/channels/1201167737163104376/1286027175048253573"
            f" or "
            f"https://discord.com/channels/1201167737163104376/1280587781638459528"
            f"\n"
        ) + unhandled_out
        await send_message_and_file(
            channel=ctx.channel,
            title=f"ERROR: >.< How did we get here...",
            message=unhandled_out,
            embed_colour=ERROR_COLOUR,
        )

    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        channel = reaction.message.channel

        # limit scope, no reason to track
        if channel.id != BOT_DEV_UNHANDLED_ERRORS_CHANNEL_ID:
            return

        # delete handled tickets
        if reaction.emoji == "🫡" and any(
            map(
                lambda r: r.name in ["Server Access", "Github Access", "Contributor"],
                user.roles,
            )
        ):
            try:
                await reaction.message.delete()
            except Exception as e:
                await channel.send(e)
