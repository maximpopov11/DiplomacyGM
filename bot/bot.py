import logging
import os
import re
import datetime
import random

from discord import Forbidden
from dotenv.main import load_dotenv

from bot.config import ERROR_COLOUR
from bot.perms import admin_only, CommandPermissionError, gm_only
from bot.utils import send_message_and_file

load_dotenv()

import discord
from discord.ext import commands

from bot import command
from diplomacy.persistence.manager import Manager

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(
    command_prefix=os.getenv("command_prefix", default="."), intents=intents
)
logger = logging.getLogger(__name__)
impdip_server = 1201167737163104376
bot_status_channel = 1284336328657600572

manager = Manager()

# List of funny, sarcastic messages
MESSAGES = [
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


@bot.event
async def on_ready():
    await bot.tree.sync()

    guild = bot.get_guild(
        impdip_server
    )  # Ensure bot is connected to the correct server
    if guild:
        channel = bot.get_channel(bot_status_channel)  # Get the specific channel
        if channel:
            message = random.choice(MESSAGES)  # Select a random message
            await channel.send(message)
        else:
            print(f"Channel with ID {bot_status_channel} not found.")
    else:
        print(f"Guild with ID {impdip_server} not found.")

    # Set bot's presence (optional)
    await bot.change_presence(activity=discord.Game(name="Impdip 🔪"))


@bot.before_invoke
async def before_any_command(ctx):
    logger.debug(
        f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}'"
    )

    # People input apostrophes that don't match what the province names are, we can catch all of that here
    # ctx.message.content = re.sub(r"[‘’`´′‛]", "'", ctx.message.content)

    # mark the message as seen
    await ctx.message.add_reaction("👍")


@bot.after_invoke
async def after_any_command(ctx: discord.ext.commands.Context):
    time_spent = datetime.datetime.now(datetime.UTC) - ctx.message.created_at

    if time_spent.total_seconds() < 10:
        level = logging.DEBUG
    else:
        level = logging.WARN

    logger.log(
        level,
        f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' - "
        f"complete in {time_spent}s",
    )


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # we shouldn't do anything if the user says something like "..."
        return

    if isinstance(error, (
            commands.CommandInvokeError,
            commands.ConversionError,
            commands.HybridCommandError
    )):
        original = error.original
    else:
        original = error

    try:
        # mark the message as failed
        await ctx.message.add_reaction("❌")
        await ctx.message.remove_reaction("👍", bot.user)
    except Exception:
        # if reactions fail, ignore and continue handling existing exception
        pass


    if isinstance(original, CommandPermissionError):
        await send_message_and_file(channel=ctx.channel, message=str(original), embed_colour=ERROR_COLOUR)
        return

    time_spent = datetime.datetime.now(datetime.UTC) - ctx.message.created_at
    logger.log(
        logging.ERROR,
        f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' - "
        f"errored in {time_spent}s\n"
    )

    if isinstance(original, Forbidden):
        await send_message_and_file(
            channel=ctx.channel,
            message=f"I do not have the correct permissions to do this.\n"
                    f"I might not be setup correctly.\n"
                    f"If this is unexpected please contact a GM or reach out in: "
                    f"https://discord.com/channels/1201167737163104376/1286027175048253573"
                    f" or "
                    f"https://discord.com/channels/1201167737163104376/1280587781638459528",
            embed_colour=ERROR_COLOUR
        )
    else:
        time_spent = datetime.datetime.now(datetime.UTC) - ctx.message.created_at

        try:
            # mark the message as failed
            await ctx.message.add_reaction("❌")
            await ctx.message.remove_reaction("👍", bot.user)
        except Exception:
            # if reactions fail continue handling error
            pass

        if isinstance(original, CommandPermissionError):

            await send_message_and_file(channel=ctx.channel, message=str(original), embed_colour=ERROR_COLOUR)
        else:
            logger.error(
                f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' - "
                f"errored in {time_spent}s\n"
            )
            logger.error(
                original
            )
            await send_message_and_file(channel=ctx.channel, message=str(original), embed_colour=ERROR_COLOUR)


class SpecView(discord.ui.View):
    def __init__(
        self,
        member: discord.Member,
        game_name: str,
        channel_url: str,
        role: discord.Role,
        cspec_role: discord.Role,
    ):
        super().__init__(timeout=None)
        self.member = member
        self.game_name = game_name
        self.url = channel_url
        self.power_role = role
        self.spec_role = cspec_role

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Accept response sent to {self.member.mention}!", ephemeral=True
        )

        await self.member.send(
            f"Response from: {self.game_name}\n"
            + f"You have been accepted as a spectator for: @{self.power_role.name}\n"
            + f"Go to {self.url} to watch them play!"
        )
        await self.member.add_roles(self.power_role, self.spec_role)

        if interaction.message:
            await interaction.message.delete()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.success)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Reject response sent to {self.member.mention}!", ephemeral=True
        )

        await self.member.send(
            f"Response from: {self.game_name}\n"
            + f"You have been rejected as a spectator for: @{self.power_role.name}\n"
        )

        if interaction.message:
            await interaction.message.delete()


@bot.tree.command(
    name="spec",
    description="Specatate a Player",
)
async def spec(interaction: discord.Interaction, power_role: discord.Role):
    guild = interaction.guild
    if not guild:
        return

    # server ignore list
    if guild.id in [impdip_server]:
        await interaction.response.send_message(
            "Can't request to spectate in the Hub server!"
        )
        return

    # ignore if DM channel
    if isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "Please use the spectate command in a Game server!"
        )
        return
    elif not interaction.channel:
        return

    if interaction.channel.name != "the-public-square":
        channel = discord.utils.find(
            lambda c: c.name == "the-public-square", guild.text_channels
        )
        if channel:
            await interaction.response.send_message(
                f"Can't request here! Go to the public square: {channel.mention}",
                ephemeral=True,
            )

        return

    # prevent spectating non-power roles
    if (
        power_role.name
        in [
            "Admin",
            "Moderators",
            "GM",
            "Heavenly Angel",
            "Player",
            "Country Spectator",
        ]
        or power_role.name.find("-orders") != -1
    ):
        await interaction.response.send_message(
            "Can't spectate that role!", ephemeral=True
        )
        return

    # get country spectator role
    cspec_role = discord.utils.find(
        lambda r: r.name == "Country Spectator", guild.roles
    )
    if not cspec_role:
        await interaction.response.send_message(
            "Could not find country spectator role! Contact GM."
        )
        return

    member = guild.get_member(interaction.user.id)
    if not member:
        return

    # if player already a player or country spec
    if any(map(lambda r: r.name in ["Player", "Country Spectator"], member.roles)):
        await interaction.response.send_message(
            "Can't request to spectate another power, you are either a Player or already a Spectator.",
            ephemeral=True,
        )

        return

    # get power channel to send request
    role_channel = discord.utils.find(
        lambda c: c.name == f"{power_role.name.lower()}-orders", guild.text_channels
    )
    role_void = discord.utils.find(
        lambda c: c.name == f"{power_role.name.lower()}-void", guild.text_channels
    )
    if not role_channel or not role_void:
        await interaction.response.send_message(
            "Please specify a playable power.", ephemeral=True
        )
        return

    # send request message to player
    out = (
        f"Spectator request from {interaction.user.mention}\n"
        + "- (if the buttons do not work, contact your GM)"
    )
    url = f"https://discord.com/channels/{guild.id}/{role_void.id}"  # link to void channel (for accept message)
    await role_channel.send(
        content=out,
        view=SpecView(member, guild.name, url, power_role, cspec_role),
    )

    # send ack to requesting user
    await interaction.response.send_message(
        "Spectator application sent! You should hear a response via DM.", ephemeral=True
    )


class SpecView(discord.ui.View):
    def __init__(
        self,
        member: discord.Member,
        game_name: str,
        admin_channel: discord.TextChannel,
        channel_url: str,
        role: discord.Role,
        cspec_role: discord.Role,
    ):
        super().__init__(timeout=None)
        self.member = member
        self.game_name = game_name
        self.admin_channel = admin_channel
        self.url = channel_url
        self.power_role = role
        self.spec_role = cspec_role

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Accept response sent to {self.member.mention}!", ephemeral=True
        )

        await self.member.send(
            f"Response from: {self.game_name}\n"
            + f"You have been accepted as a spectator for: @{self.power_role.name}\n"
            + f"Go to {self.url} to watch them play!"
        )
        await self.member.add_roles(self.power_role, self.spec_role)

        out = "[SPECTATOR LOG] {self.member.mention} approved for power {self.role.mention}"
        await self.admin_channel.send(out)

        if interaction.message:
            await interaction.message.delete()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Reject response sent to {self.member.mention}!", ephemeral=True
        )

        await self.member.send(
            f"Response from: {self.game_name}\n"
            + f"You have been rejected as a spectator for: @{self.power_role.name}\n"
        )

        out = "[SPECTATOR LOG] {self.member.mention} rejected for power {self.role.mention}"
        await self.admin_channel.send(out)

        if interaction.message:
            await interaction.message.delete()


@bot.tree.command(
    name="spec",
    description="Specatate a Player",
)
async def spec(interaction: discord.Interaction, power_role: discord.Role):
    guild = interaction.guild
    if not guild:
        return

    # server ignore list
    if guild.id in [impdip_server]:
        await interaction.response.send_message(
            "Can't request to spectate in the Hub server!", ephemeral=True
        )
        return

    # ignore if DM channel
    if isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "Please use the spectate command in a Game server!"
        )
        return
    elif not interaction.channel:
        return

    if interaction.channel.name != "the-public-square":
        channel = discord.utils.find(
            lambda c: c.name == "the-public-square", guild.text_channels
        )
        if channel:
            await interaction.response.send_message(
                f"Can't request here! Go to the public square: {channel.mention}",
                ephemeral=True,
            )

        return

    # prevent spectating non-power roles
    if (
        power_role.name
        in [
            "Admin",
            "Moderators",
            "GM",
            "Heavenly Angel",
            "GM Team",
            "Player",
            "Spectator",
            "Country Spectator",
            "Dead",
            "DiploGM",
        ]
        or power_role.name.find("-orders") != -1
    ):
        await interaction.response.send_message(
            "Can't spectate that role!", ephemeral=True
        )
        return

    # get country spectator role
    cspec_role = discord.utils.find(
        lambda r: r.name == "Country Spectator", guild.roles
    )
    if not cspec_role:
        await interaction.response.send_message(
            "Could not find country spectator role! Contact GM."
        )
        return

    member = guild.get_member(interaction.user.id)
    if not member:
        return

    # if player already a player or country spec
    if any(
        map(
            lambda r: r.name in ["Player", "Spectator", "Country Spectator", "Dead"],
            member.roles,
        )
    ):
        await interaction.response.send_message(
            "Can't request to spectate that power, you are either a Player or already a Spectator.",
            ephemeral=True,
        )

        return

    # get power channel to send request
    role_channel = discord.utils.find(
        lambda c: c.name == f"{power_role.name.lower()}-orders", guild.text_channels
    )
    role_void = discord.utils.find(
        lambda c: c.name == f"{power_role.name.lower()}-void", guild.text_channels
    )
    if not role_channel or not role_void:
        await interaction.response.send_message(
            "Please specify a playable power.", ephemeral=True
        )
        return

    admin_channel = discord.utils.find(
        lambda c: c.name == "admin-chat", guild.text_channels
    )
    if not admin_channel:
        logger.warning(f"Server: {guild.name} does not have an #admin-chat channel.")
        await interaction.response.send_message(
            "Could not process your request. (Contact Admin)", ephemeral=True
        )
        return

    out = (
        "[SPECTATOR LOG] {self.member.mention} requested for power {self.role.mention}"
    )
    await admin_channel.send(out)

    # send request message to player
    out = (
        f"{power_role.mention}: Spectator request from {interaction.user.mention}\n"
        + "- (if the buttons do not work, contact your GM)"
    )
    url = f"https://discord.com/channels/{guild.id}/{role_void.id}"  # link to void channel (for accept message)
    await role_channel.send(
        content=out,
        view=SpecView(member, guild.name, admin_channel, url, power_role, cspec_role),
    )

    # send ack to requesting user
    await interaction.response.send_message(
        "Spectator application sent! You should hear a response via DM.", ephemeral=True
    )


@bot.command(help="Checks bot listens and responds.")
async def ping(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.ping(ctx, manager)


@bot.command(hidden=True)
async def pelican(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.pelican(ctx, manager)


@bot.command(hidden=True)
async def bumble(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.bumble(ctx, manager)


@bot.command(hidden=True)
async def fish(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await ctx.message.add_reaction("🐟")
    await command.fish(ctx, manager)


@bot.command(hidden=True)
async def phish(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await ctx.message.add_reaction("🐟")
    await command.phish(ctx, manager)


@bot.command(hidden=True)
async def cheat(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.cheat(ctx, manager)


@bot.command(hidden=True)
async def advice(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.advice(ctx, manager)


@bot.command(hidden=True)
@gm_only("botsay")
async def botsay(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.botsay(ctx, manager)


@bot.command(hidden=True)
@admin_only("send a GM announcement")
async def announce(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.announce(ctx, manager)


@bot.command(hidden=True)
@admin_only("list servers")
async def servers(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.servers(ctx, manager)


@bot.command(hidden=True)
@admin_only("allocate roles to user(s)")
async def bulk_allocate_role(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.bulk_allocate_role(ctx, manager)


@bot.command(brief="Shows global fish leaderboard")
async def global_leaderboard(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.global_leaderboard(ctx, manager)


@bot.command(
    brief="Submits orders; there must be one and only one order per line.",
    description="""Submits orders: 
    There must be one and only one order per line.
    A variety of keywords are supported: e.g. '-', '->', 'move', and 'm' are all supported for a move command.
    Supplying the unit type is fine but not required: e.g. 'A Ghent -> Normandy' and 'Ghent -> Normandy' are the same
    If anything in the command errors, we recommend resubmitting the whole order message.
    *During Build phases only*, you have to specify multi-word provinces with underscores; e.g. Somali Basin would be Somali_Basin (we use a different parser during build phases)
    If you would like to use something that is not currently supported please inform your GM and we can add it.""",
    aliases=["o", "orders"],
)
async def order(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.order(ctx, manager)


@bot.command(
    brief="Removes orders for given units.",
    description="Removes orders for given units (required for removing builds/disbands). "
    "There must be one and only one order per line.",
    aliases=["remove", "rm", "removeorders"],
)
async def remove_order(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.remove_order(ctx, manager)


@bot.command(
    brief="Outputs your current submitted orders.",
    description="Outputs your current submitted orders. "
    "Use .view_map to view a sample moves map of your orders. "
    "Use the 'missing' or 'submitted' argument to view only units without orders or only submitted orders.",
    aliases=["v", "view", "vieworders", "view-orders"],
)
async def view_orders(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.view_orders(ctx, manager)


@bot.command(
    brief="Sends all previous orders",
    description="For GM: Sends orders from previous phase to #orders-log",
)
@gm_only("publish orders")
async def publish_orders(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.publish_orders(ctx, manager)


@bot.command(
    brief="Sends fog of war maps",
    description="""
    * publish_fow_moves {Country|(None) - whether or not to send for a specific country}
    """,)
@gm_only("publish fow moves")
async def publish_fow_moves(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.publish_fow_moves(ctx, manager)


@bot.command(
    brief="Sends fog of war orders",
    description="""
    * publish_fow_orders {Country|(None) - whether or not to send for a specific country}
    """,
)
@gm_only("send fow order logs")
async def publish_fow_orders(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.publish_fow_order_logs(ctx, manager)


@bot.command(
    brief="Outputs the current map with submitted orders.",
    description="""
    For GMs, all submitted orders are displayed. For a player, only their own orders are displayed.
    GMs may append true as an argument to this to instead get the svg.
    * view_map {arguments}
    Arguments: 
    * pass true|t|svg|s to return an svg
    * pass standard, dark, blue, or pink for different color modes if present
    """,
    aliases=["viewmap", "vm"],
)
async def view_map(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.view_map(ctx, manager)


@bot.command(
    brief="Outputs the current map without any orders.",
    description="""
    * view_current {arguments}
    Arguments: 
    * pass true|t|svg|s to return an svg
    * pass standard, dark, blue, or pink for different color modes if present
    """,
    aliases=["viewcurrent", "vc"],
)
async def view_current(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.view_current(ctx, manager)


@bot.command(
    brief="Outputs a interactive svg that you can issue orders in",
    aliases=["g"],
)
async def view_gui(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.view_gui(ctx, manager)


@bot.command(
    brief="Adjudicates the game and outputs the moves and results maps.",
    description="""
    GMs may append true as an argument to this command to instead get the base svg file.
    * adjudicate {arguments}
    Arguments: 
    * pass true|t|svg|s to return an svg
    * pass standard, dark, blue, or pink for different color modes if present
    """,
)
@gm_only("adjudicate")
async def adjudicate(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.adjudicate(ctx, manager)


@bot.command(brief="Rolls back to the previous game state.")
@gm_only("rollback")
async def rollback(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.rollback(ctx, manager)


@bot.command(brief="Reloads the current board with what is in the DB")
@gm_only("reload")
async def reload(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.reload(ctx, manager)


@bot.command(brief="Outputs the scoreboard.",
    description="""Outputs the scoreboard.
    In Chaos, is shortened and sorted by points, unless "standard" is an argument""",
    aliases=["leaderboard"]
)
async def scoreboard(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.get_scoreboard(ctx, manager)


@bot.command(
    brief="Edits the game state and outputs the results map.",
    description="""Edits the game state and outputs the results map. 
    There must be one and only one command per line.
    Note: you cannot edit immalleable map state (eg. province adjacency).
    The following are the supported sub-commands:
    * set_phase {spring, fall, winter}_{moves, retreats, builds}
    * set_core <province_name> <player_name>
    * set_half_core <province_name> <player_name>
    * set_province_owner <province_name> <player_name>
    * set_player_color <player_name> <hex_code>
    * create_unit {A, F} <player_name> <province_name>
    * create_dislodged_unit {A, F} <player_name> <province_name> <retreat_option1> <retreat_option2>...
    * delete_dislodged_unit <province_name>
    * delete_unit <province_name>
    * move_unit <province_name> <province_name>
    * dislodge_unit <province_name> <retreat_option1> <retreat_option2>...
    * make_units_claim_provinces {True|(False) - whether or not to claim SCs}
    * set_player_points <player_name> <integer>
    * set_player_vassal <liege> <vassal>
    * remove_relationship <player1> <player2>
    """,
)
@gm_only("edit")
async def edit(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.edit(ctx, manager)


@bot.command(brief="Clears all players orders.")
@gm_only("remove all orders")
async def remove_all(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.remove_all(ctx, manager)


@bot.command(
    brief="disables orders until .unlock_orders is run.",
    description="""disables orders until .enable_orders is run.
             Note: Currently does not persist after the bot is restarted""",
    aliases=["lock"],
)
@gm_only("lock orders")
async def lock_orders(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.disable_orders(ctx, manager)


@bot.command(
    brief="re-enables orders",
    aliases=["unlock"]
)
@gm_only("unlock orders")
async def unlock_orders(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.enable_orders(ctx, manager)


@bot.command(
    brief="outputs information about the current game",
    aliases=["i"]
)
async def info(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.info(ctx, manager)


@bot.command(
    brief="outputs information about a specific province",
    aliases=["province"],
)
async def province_info(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.province_info(ctx, manager)


@bot.command(
    brief="outputs information about a specific player",
    aliases=["player"],
)
async def player_info(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.player_info(ctx, manager)


@bot.command(brief="outputs the provinces you can see")
async def visible_info(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.visible_provinces(ctx, manager)


@bot.command(brief="publicize void for chaos")
async def publicize(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.publicize(ctx, manager)


@bot.command(brief="outputs all provinces per owner")
async def all_province_data(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.all_province_data(ctx, manager)


@bot.command(
    brief="Create a game of Imp Dip and output the map.",
    description="Create a game of Imp Dip and output the map. (there are no other variant options at this time)",
)
@gm_only("create a game")
async def create_game(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.create_game(ctx, manager)


@bot.command(
    brief="archives a category of the server",
    description="""Used after a game is done. Will make all channels in category viewable by all server members, but no messages allowed.
    * .archive [link to any channel in category]""",
)
@gm_only("archive")
async def archive(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.archive(ctx, manager)


@bot.command(
    brief="blitz",
    description="Creates all possible channels between two players for blitz in available comms channels.",
)
@gm_only("create blitz comms channels")
async def blitz(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.blitz(ctx, manager)


# @bot.command(
#     brief="wipe",
# )
# async def wipe(ctx: commands.Context) -> None:
#     await command.wipe(ctx, manager)


@bot.command(
    brief="pings players who don't have the expected number of orders.",
    description="""Pings all players in their orders channl that satisfy the following constraints:
    1. They have too many build orders, or too little or too many disband orders. As of now, waiving builds doesn't lead to a ping.
    2. They are missing move orders or retreat orders.
    You may also specify a timestamp to send a deadline to the players.
    * .ping_players <timestamp>
    """)
@gm_only("ping players")
async def ping_players(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.ping_players(ctx, manager)


@bot.command(brief="permanently deletes a game, cannot be undone")
@gm_only("delete the game")
async def delete_game(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.delete_game(ctx, manager)


@bot.command(brief="Changes your nickname")
async def nick(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.nick(ctx, manager)


@bot.command(hidden=True)
@admin_only("Execute arbitrary code")
async def exec_py(ctx: commands.Context) -> None:
    if isinstance(ctx.channel, discord.DMChannel):
        return

    await command.exec_py(ctx, manager)


def run():
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        raise RuntimeError("The DISCORD_TOKEN environment variable is not set")
