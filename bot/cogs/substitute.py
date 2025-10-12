import logging
import re

from discord import HTTPException, Role, User
from discord.ext import commands
from discord.utils import find as discord_find

from bot import config
from bot import perms
from bot.utils import get_player_by_name, send_message_and_file
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.player import Player

logger = logging.getLogger(__name__)
manager = Manager()


# HACK: Should be Slash Commands
class SubstituteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief="Places a substitute advertisement for a power",
        help="""
    Usage:
    .advertise <power> # Advertise permanent position, no extra message
    .advertise <power> <message> # Advertise permanent position, extra message
    .advertise <power> <timestamp> # Advertise temporary position, no extra message
    .advertise <power> <timestamp> <message> # Advertise temporary position, extra message
        """,
    )
    @perms.gm_only("advertise for a substitute")
    async def advertise(
        self,
        ctx: commands.Context,
        power_role: Role,
        timestamp: str | None = None,
        *message,
    ):
        guild = ctx.guild
        if not guild:
            return

        if len(message) == 0:
            message = "No message given."
        else:
            message = " ".join(message)
        
        _hub = ctx.bot.get_guild(config.IMPDIP_SERVER_ID)
        if not _hub:
            raise perms.CommandPermissionError(
                "Can't advertise as can't access the Imperial Diplomacy Hub Server."
            )

        interested_sub_ping = ""
        interested_sub_role = discord_find(
            lambda r: r.name == "Interested Substitute", _hub.roles
        )
        if interested_sub_role:
            interested_sub_ping = f"{interested_sub_role.mention}\n"

        board = manager.get_board(guild.id)
        try:
            power: Player = board.get_player(power_role.name)
        except ValueError:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Did not mention a Player role.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        # GET TIMESTAMP FOR TEMP SUB SPECIFICATION
        if timestamp is not None:
            timestamp_re = r"<t:(\d+):[a-zA-Z]>"
            match = re.match(
                timestamp_re,
                timestamp,
            )

            if match:
                timestamp = f"<t:{match.group(1)}:D>"
            else:
                message = timestamp + " " + message
                timestamp = None

        sub_period = (
            "Permanent" if timestamp is None else f"Temporary until {timestamp}"
        )

        # GET CHANNELS FOR POST / REDIRECTS
        ticket_channel = ctx.bot.get_channel(
            config.IMPDIP_SERVER_SUBSTITUTE_TICKET_CHANNEL_ID
        )
        if not ticket_channel:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Could not find the channel where substitute tickets can be created",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        advertise_channel = ctx.bot.get_channel(
            config.IMPDIP_SERVER_SUBSTITUTE_ADVERTISE_CHANNEL_ID
        )
        if not advertise_channel:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Could not find the channel meant for advertisements",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        title = f"Substitute Advertisement"
        out = f"""
    {interested_sub_ping}
    Period: {sub_period}
    Game: {guild.name}
    Phase: {board.phase.name} {board.get_year_str()}
    Power: {power.name}
    SC Count: {len(power.centers)}
    VSCC: {round(power.score() * 100, 2)}%

    Message: {message}

    If you are interested, please go to {ticket_channel.mention} to create a ticket, and remember to ping {ctx.author.mention} so they know you're asking.
        """

        file, file_name = manager.draw_map(guild.id, color_mode="standard")
        await send_message_and_file(
            channel=advertise_channel,
            title=title,
            message=out,
            file=file,
            file_name=file_name,
            convert_svg=True,
            file_in_embed=True,
        )

        # create a ghost ping of "@Interested Substitute" since embeds don't notify
        try:
            msg = await advertise_channel.send(interested_sub_ping)
            await msg.delete(delay=5)
        except HTTPException as e:
            logger.warning(f"failed to ping interested substitutes: {e}")

    @commands.command(
        brief="Handles the in/out substitution of two users",
        help="""
        TODO: Add more explicit support for temporary substitutes...
        In the mean time, use the reason argument to explain a temp sub

        Usage:
            .substitute <usernameA> <usernameB> @France <reason>
            .substitute <pingUserA> <pingUserB> @Mughal
        """,
    )
    @perms.gm_only("substitute a player")
    async def substitute(
        self,
        ctx: commands.Context,
        out_user: User,
        in_user: User,
        power_role: Role,
        *reason,
    ):
        guild = ctx.guild
        if not guild:
            return

        board = manager.get_board(guild.id)

        if len(reason) == 0:
            reason = "No reason provided."
        else:
            reason = " ".join(reason)
        
        # HACK: Need to create an approved server list for commands
        override = False
        if not guild.name.startswith("Imperial Diplomacy") and not override:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="You're not allowed to do that in this server.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        in_member = guild.get_member(in_user.id)
        if not in_member:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Can't substitute a player that is not in the server!",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        if not get_player_by_name(power_role.name, manager, guild.id):
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Did not supply a Player role.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        # log a substitution is occurring in the gm space
        # TODO: Update Substitution Logging to include Reputation after Bot Integration
        logc = ctx.bot.get_channel(config.IMPDIP_SERVER_SUBSTITUTE_LOG_CHANNEL_ID)
        out = (
            f"Game: {guild.name}\n"
            + f"- Guild ID: {guild.id}\n"
            + f"In: {in_user.mention}[{in_user.name}]\n"
            + f"Out: {out_user.mention}[{out_user.name}]\n"
            + f"Phase: {board.phase.name} {board.get_year_str()}\n"
            + f"Reason: {reason}"
        )
        await send_message_and_file(channel=logc, message=out)

        # fetch relevant roles to swap around on the users
        player_role = discord_find(lambda r: r.name == "Player", guild.roles)
        if not player_role:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Can't proceed with automatic substitution processing: Couldn't find 'Player' role.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        orders_role = discord_find(
            lambda r: r.name == f"orders-{power_role.name.lower()}", guild.roles
        )
        if not orders_role:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message=f"Can't proceed with automatic substitution processing: Couldn't find 'orders-{power_role.name.lower()}' role.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        cspec_role = discord_find(lambda r: r.name == "Country Spectator", guild.roles)
        if not cspec_role:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Can't proceed with automatic substitution processing: Couldn't find 'Country Spectator' role.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        # if incoming is currently a player
        if player_role in in_member.roles:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Can't substitute in an existing player!",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        # if incoming is a country spec but not of current player
        if cspec_role in in_member.roles and power_role not in in_member.roles:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Incoming player is a country spectator for another power!",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        # has incoming player spectated before
        prev_spec = manager.get_spec_request(guild.id, in_user.id)
        if prev_spec:
            prev_spec_role = ctx.bot.get_role(prev_spec.role_id)

            # previous spec of another power
            if prev_spec.role_id != power_role.id:
                await send_message_and_file(
                    channel=ctx.channel,
                    title="Error",
                    message=f"Incoming player has previously spectated for power {prev_spec_role.mention}",
                    embed_colour=config.ERROR_COLOUR,
                )
                return

        # PROCESS ROLE ASSIGNMENTS
        out = f"Outgoing Player: {out_user.name}\n"
        out_member = guild.get_member(out_user.id)
        if out_member:
            prev_roles = list(
                filter(lambda r: r in out_member.roles, [player_role, orders_role])
            )  # roles to remove if they exist
            prev_role_names = ", ".join(map(lambda r: r.mention, prev_roles))
            out += f"- Previous Roles: {prev_role_names}\n"

            new_roles = [cspec_role]  # roles to add
            new_role_names = ", ".join(map(lambda r: r.mention, new_roles))
            out += f"- New Roles: {new_role_names}\n"

            try:
                await out_member.remove_roles(*prev_roles, reason="Substitution")
                await out_member.add_roles(*new_roles)
            except HTTPException:
                out += f"[ERROR] Failed to swap roles for outgoing player: {out_user.name}\n"

        out += f"Incoming Player: {in_user.name}\n"
        prev_roles = list(
            filter(lambda r: r in in_member.roles, [cspec_role])
        )  # roles to remove if they exist
        prev_role_names = ", ".join(map(lambda r: r.mention, prev_roles))
        out += f"- Previous Roles: {prev_role_names}\n"

        new_roles = [player_role, power_role, orders_role]  # roles to add
        new_role_names = ", ".join(map(lambda r: r.mention, new_roles))
        out += f"- New Roles: {new_role_names}\n"

        try:
            await in_member.remove_roles(*prev_roles, reason="Substitution")
            await in_member.add_roles(*new_roles)
        except HTTPException:
            out += f"[ERROR] Failed to swap roles for outgoing player: {out_user.name}"

        await send_message_and_file(
            channel=ctx.channel, title="Substitution results", message=out
        )


async def setup(bot):
    cog = SubstituteCog(bot)
    await bot.add_cog(cog)
