import logging
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import find as discord_find

from bot import config
from bot import perms
from bot import utils
from bot.utils import get_player_by_name, send_message_and_file
from diplomacy.persistence.manager import Manager

logger = logging.getLogger(__name__)
manager = Manager()

SERVER_OVERRIDE = True


class SlashSubstituteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="advertise",
        description="Places a substitute advertisement for a power",
        extras={
            "help": """
    Usage:
    .advertise <power> # Advertise permanent position, no extra message
    .advertise <power> <message> # Advertise permanent position, extra message
    .advertise <power> <timestamp> # Advertise temporary position, no extra message
    .advertise <power> <timestamp> <message> # Advertise temporary position, extra message
        """
        },
    )
    async def advertise(
        self,
        interaction: discord.Interaction,
        power_role: discord.Role,
        timestamp: Optional[str] = None,
        message: Optional[str] = "No message given.",
    ):
        """
        Create an advertisement for substitutes automatically, to enforce a standard of information that should be contained within.

        Process:
            1. If nothing is given for *message, set to string "No message given.", else join with space delimiter
            2. Find the Hub Server and Get Interested Substitute Role
            3. Get the Player object from the Boardstate using the supplied power_role
            4. Check that timestamp arg is a valid timestamp, else prepend to message.
            5. Get channel to create tickets and channel to post advertisement
            6. Format Player data (period, game_name, game_phase, power, sc count, vscc)
            7. Post advertisement in correct channel
            8. Ghost Ping "Interested Substitute" to function as embed ping
                a. TODO: look into text as well as embed to remove this


        Parameters
        ----------
        power_role (discord.Role): Role of the power that has requested a substitution
        timestamp (str | None): Optional timestamp for declaring temporary substitute period
        *message (tuple): Analagous to *args, for purpose of collecting a string to inform advert

        Returns
        -------
        None

        """
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            return

        bot = interaction.client

        # TODO: app_commands permissions check decorators
        if not perms.is_gm(interaction.user):
            await interaction.response.send_message(
                "You are not allowed to use `.advertise`!", ephemeral=True
            )
            return

        if not utils.is_gm_channel(interaction.channel):
            await interaction.response.send_message(
                "You are not allowed to use `.advertise` here!", ephemeral=True
            )
            return

        # HACK: Should create an approved list of servers
        if not SERVER_OVERRIDE and not guild.name.startswith("Imperial Diplomacy"):
            await interaction.response.send_message(
                "You are not permitted to use `.advertise` in this server!",
                ephemeral=True,
            )
            return

        locations = {
            "hub_server": bot.get_guild(config.IMPDIP_SERVER_ID),
            "advertise_channel": bot.get_channel(
                config.IMPDIP_SERVER_SUBSTITUTE_ADVERTISE_CHANNEL_ID
            ),
            "tickets_channel": bot.get_channel(
                config.IMPDIP_SERVER_SUBSTITUTE_TICKET_CHANNEL_ID
            ),
        }

        if any(map(lambda pair: pair[1] is None, locations.items())):
            out = "Could not access the relevant locations:\n"
            for k, v in locations.items():
                if v is None:
                    out += f"- {k}\n"

            await send_message_and_file(
                channel=interaction.channel,
                title="/advertise output",
                message=f"{out}",
                embed_colour=config.ERROR_COLOUR,
            )
            await interaction.response.send_message("Failure!", ephemeral=True)
            return

        interested_sub_role = discord_find(
            lambda r: r.name == "Interested Substitute", locations["hub_server"].roles
        )
        if not interested_sub_role:
            await send_message_and_file(
                channel=interaction.channel,
                message="Could not find the role for interested substitutes.",
            )
            return

        board = manager.get_board(guild.id)
        player = get_player_by_name(power_role.name, manager, guild.id)
        if not player:
            out = f"Could not find Player object for given role {power_role.mention}"
            await send_message_and_file(
                channel=interaction.channel,
                title="/advertise output",
                message=f"{out}",
                embed_colour=config.ERROR_COLOUR,
            )
            await interaction.response.send_message("Failure!", ephemeral=True)
            return

        await interaction.response.defer()

        if timestamp is None:
            timestamp_msg = "Permanent"
        else:
            match = re.match(r"<t:(\d{10}):?(f|F|d|D|t|T|R)>", timestamp)
            if match:
                timestamp_msg = f"until <t:{match.group(1)}:F>"
            else:
                out = f"Improper value for argument 'timestamp'"
                await send_message_and_file(
                    channel=interaction.channel,
                    title="/advertise output",
                    message=f"{out}",
                    embed_colour=config.ERROR_COLOUR,
                )
                await interaction.followup.send("Failure!", ephemeral=True)
                return

        
        out = (
            f"Period: {timestamp_msg}\n"
            f"Game: {guild.name}\n"
            f"Phase: {board.phase.name} {board.get_year_str()}\n"
            f"Power: {power_role.name}\n"
            f"SC Count: {len(player.centers)}\n"
            f"VSCC: {round(player.score() * 100, 2)}%\n"
            "\n"
            f"Message: {message}\n"
            "\n"
            f"If you are interested, please go to {locations['tickets_channel'].mention} and create a ticket. Don't forget to ping {interaction.user.mention}[{interaction.user.name}] so that they know you want to join the game!"
        )
        file, file_name = manager.draw_map_for_board(
            board, player_restriction=None, draw_moves=False, color_mode="standard"
        )

        link = await send_message_and_file(
            channel=locations["advertise_channel"],
            title="Substitute Advertisemenet",
            message=out,
            file=file,
            file_name=file_name,
            convert_svg=True,
        )
        try:
            msg = await locations["advertise_channel"].send(interested_sub_role.mention)
            await msg.delete(delay=2)
        except discord.HTTPException as e:
            logger.warning(f"failed to ping interested substitutes: {e}")

        await interaction.followup.send(
            f"Advertisement put out for {power_role.mention}: {link.jump_url}"
        )

    @app_commands.command(
        name="substitute",
        description="Handles the in/out substitution of two users",
        extras={
            "help": """
        TODO: Add more explicit support for temporary substitutes...
        In the mean time, use the reason argument to explain a temp sub

        Usage:
            .substitute <usernameA> <usernameB> @France <reason>
            .substitute <pingUserA> <pingUserB> @Mughal
        """
        },
    )
    async def substitute(
        self,
        interaction: discord.Interaction,
        incoming_user: discord.User,
        outgoing_username: str,
        power_role: discord.Role,
        recommended_penalty: Optional[int],
        reason: Optional[str] = "No reason provided.",
    ):
        """
        Easily handle automatic processing of substitutes, both role switching and documentation.
        Primarily created to enforce correct outputs for the Reputation Tracker...


        Process:
            1. If nothing is given for *reason, set to string "No reason provided.", else join with space delimiter
            2. Validate server is within the Reputation system (for output to Reputation-Tracker)
                a. guild.name.startswith("Imperial Diplomacy")
            3. Check that incoming player is within the server for processing
                a. Check that the role to provide the incoming player is an actual Power role for gametype
            4. Log incoming and outgoing users to #Reputation-Tracker
            5. Obtain relevant roles for auto-switching (Player, <power>-orders, Country Spectator)
            6. Check substitution is correct
                a. Incoming is not a current player
                b. Incoming player is/has not spectating another power
            7. Remove any Player roles on outgoing player, add new position roles
            7. Remove any Spectator roles on incoming player, add new position roles

        Parameters
        ----------
        out_user (discord.User): Prefers mention, can use a username if accurate
        in_user (discord.User): Prefers mention, can use a username if accurate
        power_role (discord.Role): Prefers mention, can use a name if accurate
        *reason (tuple): Analagous to *args, for purpose of collecting a string to inform advert

        Returns
        -------
        None

        """
        guild = interaction.guild
        bot = interaction.client
        if not guild or not isinstance(interaction.user, discord.Member):
            return

        # TODO: app_commands permissions check decorators
        if not perms.is_gm(interaction.user):
            await interaction.response.send_message(
                "You are not allowed to use `.substitute`!", ephemeral=True
            )
            return

        if not utils.is_gm_channel(interaction.channel):
            await interaction.response.send_message(
                "You are not allowed to use `.substitute` here!", ephemeral=True
            )
            return

        # HACK: Should create an approved list of servers
        if not SERVER_OVERRIDE and not guild.name.startswith("Imperial Diplomacy"):
            await interaction.response.send_message(
                "You are not permitted to use `.substitute` in this server!",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # CHECK ALL LOCATIONS ARE AVAILABLE
        locations = {
            "hub_server": bot.get_guild(config.IMPDIP_SERVER_ID),
            "tracker_channel": bot.get_channel(
                config.IMPDIP_SERVER_SUBSTITUTE_LOG_CHANNEL_ID
            ),
        }

        if any(map(lambda pair: pair[1] is None, locations.items())):
            out = "Could not access the relevant locations:\n"
            for k, v in locations.items():
                if v is None:
                    out += f"- {k}\n"

            await send_message_and_file(
                channel=interaction.channel,
                title="Error running /substitute",
                message=f"{out}",
                embed_colour=config.ERROR_COLOUR,
            )
            await interaction.response.send_message("Failure!", ephemeral=True)
            return

        # CHECK A VALID PLAYER HAS BEEN GIVEN
        player = utils.get_player_by_name(power_role.name, manager, guild.id)
        if not player:
            out = f"Could not find Player object for given role {power_role.mention}"
            await send_message_and_file(
                channel=interaction.channel,
                title="Error running /substitute",
                message=f"{out}",
                embed_colour=config.ERROR_COLOUR,
            )
            await interaction.response.send_message("Failure!", ephemeral=True)
            return

        # CHECK ALL ROLES ARE AVAILABLE
        roles = {
            "power": power_role,
            "power-orders": discord_find(
                lambda r: r.name == f"orders-{power_role.name.lower()}", guild.roles
            ),
            "player": discord_find(lambda r: r.name == f"Player", guild.roles),
            "cspec": discord_find(
                lambda r: r.name == f"Country Spectator", guild.roles
            ),
        }

        if any(map(lambda pair: pair[1] is None, roles.items())):
            out = "Could not access the relevant roles:\n"
            for k, v in roles.items():
                if v is None:
                    out += f"- {k}\n"

            await send_message_and_file(
                channel=interaction.channel,
                title="Error running /substitute",
                message=f"{out}",
                embed_colour=config.ERROR_COLOUR,
            )
            await interaction.response.send_message("Failure!", ephemeral=True)
            return

        if roles["player"] in incoming_user.roles:
            await interaction.followup.send(
                f"{incoming_user.mention} is already a player!"
            )
            return

        if (
            roles["cspec"] in incoming_user.roles
            and power_role not in incoming_user.roles
        ):
            await interaction.followup.send(
                f"{incoming_user.mention} is a Country Spectator for another Power!"
            )
            return

        prev_spec = manager.get_spec_request(guild.id, incoming_user.id)
        if prev_spec and prev_spec.role_id != power_role.id:
            other = guild.get_role(prev_spec.role_id)
            if not other:
                await send_message_and_file(
                    channel=interaction.channel,
                    embed_colour=config.PARTIAL_ERROR_COLOUR,
                    message=f"{incoming_user.mention} is previously spectated a currently unknown power.",
                )
            else:
                await interaction.followup.send(
                    f"{incoming_user.mention} is previously spectated {other.mention}!"
                )
                return

        # OUTPUT TO REPUTATION-TRACKER
        outgoing_username = outgoing_username.strip()
        if outgoing_username.startswith("@"):
            outgoing_username = outgoing_username[1:]

        match = re.match(r"<@(\d+)>", outgoing_username)
        if match:
            await interaction.followup.send(
                "Argument `outgoing_username` does not support user mentions."
            )
            return
        else:
            outgoing_user = discord_find(
                lambda m: m.name == outgoing_username, guild.members
            )

        # try to get outgoing user: if username provided and not in game server but still in the hub
        if not outgoing_user:
            outgoing_user = discord_find(
                lambda m: m.name == outgoing_username, locations["hub_server"].members
            )

        try:
            await incoming_user.add_roles(
                power_role, roles["power-orders"], roles["player"]
            )
            await incoming_user.remove_roles(roles["cspec"])

            if not outgoing_user:
                await interaction.followup.send(
                    f"{outgoing_user} not in this server or the hub server."
                )
            else:
                outgoing_member = guild.get_member(outgoing_user.id)
                if outgoing_member:
                    await outgoing_member.add_roles(power_role, roles["cspec"])
                    await outgoing_member.remove_roles(
                        roles["power-orders"], roles["player"]
                    )
        except discord.HTTPException as e:
            await send_message_and_file(
                channel=interaction.channel,
                title="Could not completely auto-handle Role switching...",
                message=f"Will have to be done manually.\n`{e}`",
                embed_colour=config.ERROR_COLOUR,
            )
            pass

        # OUTPUT TO REPUTATION TRACKER
        board = manager.get_board(guild.id)
        phase = f"{board.phase.name} {board.get_year_str()}"
        out = (
            f"Game: {guild.name}\n"
            f"- GuildID: {guild.id}\n"
            f"In: {incoming_user.mention}[{incoming_user.name}]\n"
            f"Out: {outgoing_user.mention if outgoing_user else '(null)'}[{outgoing_username}]\n"
            f"Phase: {phase}\n"
            f"Reason: {reason}"
        )

        if recommended_penalty:
            out += f"\nRecommended Penalty: {recommended_penalty}"

        link = await send_message_and_file(
            channel=locations["tracker_channel"], message=out
        )

        sub_tracking = discord_find(
            lambda c: c.name == "player-sub-tracking", guild.channels
        )
        if sub_tracking:
            link = await send_message_and_file(channel=sub_tracking, message=out)

        await interaction.followup.send(
            f"Substitution made for {power_role.mention}: {link.jump_url}"
        )


async def setup(bot):
    cog = SlashSubstituteCog(bot)
    await bot.add_cog(cog)
