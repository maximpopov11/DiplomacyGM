import logging
import re

from discord import (
    CategoryChannel,
    HTTPException,
    Member,
    PermissionOverwrite,
    Role,
    Thread,
    User,
)
from discord.ext import commands
from discord.utils import find as discord_find

from bot import config
from bot.parse_edit_state import parse_edit_state
from bot import perms
from bot.utils import (
    discord_formatted_name,
    get_orders,
    get_orders_log,
    get_player_by_channel,
    get_player_by_name,
    get_role_by_player,
    is_gm,
    log_command,
    send_message_and_file,
)
from diplomacy.persistence import phase
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.order import Disband, Build
from diplomacy.persistence.player import Player
from diplomacy.persistence.manager import Manager


logger = logging.getLogger(__name__)
manager = Manager()


class GameManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief="Create a game of Imp Dip and output the map.",
        description="Create a game of Imp Dip and output the map. (there are no other variant options at this time)",
    )
    @perms.gm_only("create a game")
    async def create_game(self, ctx: commands.Context) -> None:
        gametype = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        if gametype == "":
            gametype = "impdip"
        else:
            gametype = gametype.removeprefix(" ")

        message = manager.create_game(ctx.guild.id, gametype)
        log_command(logger, ctx, message=message)
        await send_message_and_file(channel=ctx.channel, message=message)

    @commands.command(brief="permanently deletes a game, cannot be undone")
    @perms.gm_only("delete the game")
    async def delete_game(self, ctx: commands.Context) -> None:
        manager.total_delete(ctx.guild.id)
        log_command(logger, ctx, message=f"Deleted game")
        await send_message_and_file(channel=ctx.channel, title="Deleted game")

    @commands.command(brief="")
    @perms.gm_only("archive the category")
    async def archive(self, ctx: commands.Context) -> None:
        categories = [channel.category for channel in ctx.message.channel_mentions]
        if not categories:
            await send_message_and_file(
                channel=ctx.channel,
                message="This channel is not part of a category.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        for category in categories:
            for channel in category.channels:
                overwrites = channel.overwrites

                # Remove all permissions except for everyone
                overwrites.clear()
                overwrites[ctx.guild.default_role] = PermissionOverwrite(
                    read_messages=True, send_messages=False
                )

                # Apply the updated overwrites
                await channel.edit(overwrites=overwrites)

        message = f"The following catagories have been archived: {' '.join([catagory.name for catagory in categories])}"
        log_command(logger, ctx, message=f"Archived {len(categories)} Channels")
        await send_message_and_file(channel=ctx.channel, message=message)

    @commands.command(
        brief="pings players who don't have the expected number of orders.",
        description="""Pings all players in their orders channel that satisfy the following constraints:
        1. They have too many build orders, or too little or too many disband orders. As of now, waiving builds doesn't lead to a ping.
        2. They are missing move orders or retreat orders.
        You may also specify a timestamp to send a deadline to the players.
        * .ping_players <timestamp>
        """,
    )
    @perms.gm_only("ping players")
    async def ping_players(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        board = manager.get_board(guild.id)

        # extract deadline argument
        timestamp = re.match(
            r"<t:(\d+):[a-zA-Z]>",
            ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip(),
        )
        if timestamp:
            timestamp = f"<t:{timestamp.group(1)}:R>"

        # get abstract player information
        player_roles: set[Role] = set()
        for r in guild.roles:
            if config.is_player_role(r.name):
                player_roles.add(r)

        if len(player_roles) == 0:
            log_command(logger, ctx, message=f"No player role found")
            await send_message_and_file(
                channel=ctx.channel,
                message="No player category found",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        player_channels: dict[str, TextChannel] = dict()
        for c in guild.categories:
            if config.is_player_category(c.name):
                for channel in c.channels:
                    if channel.name.endswith(config.player_channel_suffix):
                        player_name = channel.name[:-len(config.player_channel_suffix)]
                        player_channels[player_name] = channel

        if len(player_channels) == 0:
            log_command(logger, ctx, message=f"No player channels found")
            await send_message_and_file(
                channel=ctx.channel,
                message="No player channels found",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        # ping required players
        pinged_players = 0
        failed_players = []
        response = ""
        for player in board.players:
            if phase.is_builds(board.phase):
                count = len(player.centers) - len(player.units)

                current = player.waived_orders
                has_disbands = False
                has_builds = player.waived_orders > 0
                for order in player.build_orders:
                    if isinstance(order, Disband):
                        current -= 1
                        has_disbands = True
                    elif isinstance(order, Build):
                        current += 1
                        has_builds = True

                if has_builds and has_disbands:
                    response = f"you have both build and disband orders. Please get this looked at."
                elif count == 0:
                    continue
                elif count >= 0:
                    available_centers = [
                        center
                        for center in player.centers
                        if center.unit is None
                        and (
                            center.core == player
                            or "build anywhere" in board.data.get("adju flags", [])
                        )
                    ]
                    available = min(len(available_centers), count)

                    difference = abs(current - available)
                    order_text = "order" if abs(current - count) == 1 else "orders"
                    if current > available:
                        response = f"you have {difference} more build {order_text} than possible. Please get this looked at."
                    elif current < available:
                        response = f"you have {difference} less build {order_text} than necessary. Make sure that you want to waive."
                else:
                    if current < count:
                        response = f"you have {difference} more disband {order_text} than necessary. Please get this looked at."
                    elif current > count:
                        response = f"you have {difference} less disband {order_text} than required. Please get this looked at."
            else:
                if phase.is_retreats(board.phase):
                    in_moves = lambda u: u == u.province.dislodged_unit
                else:
                    in_moves = lambda _: True

                missing = [
                    unit
                    for unit in player.units
                    if unit.order is None and in_moves(unit)
                ]

                if not missing:
                    continue
                unit_text = "unit" if len(missing) == 1 else "units"
                response = f"you are missing moves for the following {len(missing)} {unit_text}:"
                for unit in sorted(
                    missing, key=lambda _unit: _unit.province.name
                ):
                    response += f"\n{unit}"

            if discord_formatted_name(player.name) not in player_channels:
                await ctx.send(f"No channel for {player.name}")
                continue
            channel = player_channels[discord_formatted_name(player.name)]
            
            role = get_role_by_player(player, guild.roles)
            if role is None:
                await ctx.send(f"No Role for {player.name}")
                continue

            if board.is_chaos():
                users = set()
                # Find users with access to this channel
                for overwritter, permission in channel.overwrites.items():
                    if isinstance(overwritter, Member):
                        if permission.view_channel:
                            users.add(overwritter)
                        pass
            else:
                # Find users which have a player role to not ping spectators
                users = set(
                    filter(
                        lambda m: len(set(m.roles) & player_roles) > 0, role.members
                    )
                )

            if len(users) == 0:
                failed_players.append(player)

                # HACK: ping role in case of no players
                users.add(role)

            pinged_players += 1
            response = f"Hey {''.join([u.mention for u in users])}, {response}"
            if timestamp:
                response += f"\n The orders deadline is {timestamp}."
            await channel.send(response)

        log_command(logger, ctx, message=f"Pinged {pinged_players} players")
        await send_message_and_file(
            channel=ctx.channel, title=f"Pinged {pinged_players} players"
        )

        if len(failed_players) > 0:
            failed_players_str = "\n- ".join([player.name for player in failed_players])
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Failed to find a player for the following:\n- {failed_players_str}",
            )

    @commands.command(
        brief="disables orders until .unlock_orders is run.",
        description="""disables orders until .enable_orders is run.
                 Note: Currently does not persist after the bot is restarted""",
        aliases=["lock"],
    )
    @perms.gm_only("lock orders")
    async def lock_orders(self, ctx: commands.Context) -> None:
        board = manager.get_board(ctx.guild.id)
        board.orders_enabled = False
        log_command(logger, ctx, message="Locked orders")
        await send_message_and_file(
            channel=ctx.channel,
            title="Locked orders",
            message=f"{board.phase.name} {board.get_year_str()}",
        )

    @commands.command(brief="re-enables orders", aliases=["unlock"])
    @perms.gm_only("unlock orders")
    async def unlock_orders(self, ctx: commands.Context) -> None:
        board = manager.get_board(ctx.guild.id)
        board.orders_enabled = True
        log_command(logger, ctx, message="Unlocked orders")
        await send_message_and_file(
            channel=ctx.channel,
            title="Unlocked orders",
            message=f"{board.phase.name} {board.get_year_str()}",
        )

    @commands.command(brief="Clears all players orders.")
    @perms.gm_only("remove all orders")
    async def remove_all(self, ctx: commands.Context) -> None:
        board = manager.get_board(ctx.guild.id)
        for unit in board.units:
            unit.order = None

        database = get_connection()
        database.save_order_for_units(board, board.units)
        log_command(logger, ctx, message="Removed all Orders")
        await send_message_and_file(channel=ctx.channel, title="Removed all Orders")

    @commands.command(
        brief="Sends all previous orders",
        description="For GM: Sends orders from previous phase to #orders-log",
    )
    @perms.gm_only("publish orders")
    async def publish_orders(self, ctx: commands.Context) -> None:
        board = manager.get_previous_board(ctx.guild.id)
        if not board:
            await send_message_and_file(
                channel=ctx.channel,
                title="Failed to get previous phase",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        try:
            order_text = get_orders(board, None, ctx, fields=True)
        except RuntimeError as err:
            logger.error(err, exc_info=True)
            log_command(
                logger,
                ctx,
                message=f"Failed for an unknown reason",
                level=logging.ERROR,
            )
            await send_message_and_file(
                channel=ctx.channel,
                title="Unknown Error: Please contact your local bot dev",
                embed_colour=config.ERROR_COLOUR,
            )
            return
        orders_log_channel = get_orders_log(ctx.guild)
        if not orders_log_channel:
            log_command(
                logger,
                ctx,
                message=f"Could not find orders log channel",
                level=logging.WARN,
            )
            await send_message_and_file(
                channel=ctx.channel,
                title="Could not find orders log channel",
                embed_colour=config.ERROR_COLOUR,
            )
            return
        else:
            await send_message_and_file(
                channel=orders_log_channel,
                title=f"{board.phase.name} {board.get_year_str()}",
                fields=order_text,
            )
            log_command(logger, ctx, message=f"Successfully published orders")
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Sent Orders to {orders_log_channel.mention}",
            )

    @commands.command(
        brief="Adjudicates the game and outputs the moves and results maps.",
        description="""
        GMs may append true as an argument to this command to instead get the base svg file.
        * adjudicate {arguments}
        Arguments: 
        * pass true|t|svg|s to return an svg
        * pass standard, dark, blue, or pink for different color modes if present
        """,
    )
    @perms.gm_only("adjudicate")
    async def adjudicate(self, ctx: commands.Context) -> None:
        board = manager.get_board(ctx.guild.id)

        arguments = (
            ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
            .strip()
            .lower()
            .split()
        )
        return_svg = not ({"true", "t", "svg", "s"} & set(arguments))
        color_arguments = list(config.color_options & set(arguments))
        color_mode = color_arguments[0] if color_arguments else None
        old_turn = (board.get_year_str(), board.phase)
        # await send_message_and_file(channel=ctx.channel, **await view_map(ctx, manager))
        # await send_message_and_file(channel=ctx.channel, **await view_orders(ctx, manager))
        manager.adjudicate(ctx.guild.id)

        log_command(
            logger,
            ctx,
            message=f"Adjudication Sucessful for {board.phase.name} {board.get_year_str()}",
        )
        file, file_name = manager.draw_moves_map(
            ctx.guild.id, None, color_mode, old_turn
        )
        await send_message_and_file(
            channel=ctx.channel,
            title=f"{old_turn[1].name} {old_turn[0]}",
            message="Moves Map",
            file=file,
            file_name=file_name,
            convert_svg=return_svg,
            file_in_embed=False,
        )
        file, file_name = manager.draw_current_map(ctx.guild.id, color_mode)
        await send_message_and_file(
            channel=ctx.channel,
            title=f"{board.phase.name} {board.get_year_str()}",
            message="Results Map",
            file=file,
            file_name=file_name,
            convert_svg=return_svg,
            file_in_embed=False,
        )

    @commands.command(brief="Rolls back to the previous game state.")
    @perms.gm_only("rollback")
    async def rollback(self, ctx: commands.Context) -> None:
        message = manager.rollback(ctx.guild.id)
        log_command(logger, ctx, message=message["message"])
        await send_message_and_file(channel=ctx.channel, **message)

    @commands.command(brief="Reloads the current board with what is in the DB")
    @perms.gm_only("reload")
    async def reload(self, ctx: commands.Context) -> None:
        message = manager.reload(ctx.guild.id)
        log_command(logger, ctx, message=message["message"])
        await send_message_and_file(channel=ctx.channel, **message)

    @commands.command(
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
        * set_game_name <game_name>
        """,
    )
    @perms.gm_only("edit")
    async def edit(self, ctx: commands.Context) -> None:
        edit_commands = ctx.message.content.removeprefix(
            ctx.prefix + ctx.invoked_with
        ).strip()
        message = parse_edit_state(edit_commands, manager.get_board(ctx.guild.id))
        log_command(logger, ctx, message=message["title"])
        await send_message_and_file(channel=ctx.channel, **message)

    @commands.command(
        help="""Places a substitute advertisement for a power

    Usage:
    .advertise <power> # Advertise permanent position, no extra message
    .advertise <power> <message> # Advertise permanent position, extra message
    .advertise <power> <timestamp> # Advertise temporary position, no extra message
    .advertise <power> <timestamp> <message> # Advertise temporary position, extra message
        """
    )
    @perms.gm_only("advertise for a substitute")
    async def advertise(
        self,
        ctx: commands.Context,
        power_role: Role,
        timestamp: str | None = None,
        message: str = "No message given.",
    ):
        guild = ctx.guild
        if not guild:
            return

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

        file, file_name = manager.draw_current_map(guild.id, "standard")
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

    @commands.command(help="Handles the in/out substitution of two users")
    @perms.gm_only("substitute a player")
    async def substitute(
        self,
        ctx: commands.Context,
        manager: Manager,
        out_user: User,
        in_user: User,
        power_role: Role,
        reason: str = "No reason given.",
    ):
        guild = ctx.guild
        if not guild:
            return

        board = manager.get_board(guild.id)

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

    @commands.command(
        brief="blitz",
        description="Creates all possible channels between two players for blitz in available comms channels.",
    )
    @perms.gm_only("create blitz comms channels")
    async def blitz(self, ctx: commands.Context) -> None:
        board = manager.get_board(ctx.guild.id)
        cs = []
        pla = sorted(board.players, key=lambda p: p.name)
        for p1 in pla:
            for p2 in pla:
                if p1.name < p2.name:
                    c = f"{p1.name}-{p2.name}"
                    cs.append((c, p1, p2))

        cos: list[CategoryChannel] = []

        guild = ctx.guild

        for category in guild.categories:
            if category.name.lower().startswith("comms"):
                cos.append(category)

        available = 0
        for cat in cos:
            available += 50 - len(cat.channels)

        # if available < len(cs):
        #     await send_message_and_file(channel=ctx.channel, message="Not enough available comms")
        #     return

        name_to_player: dict[str, Player] = dict()
        player_to_role: dict[Player | None, Role] = dict()
        for player in board.players:
            name_to_player[player.name.lower()] = player

        spectator_role = None

        for role in guild.roles:
            if role.name.lower() == "spectator":
                spectator_role = role

            player = name_to_player.get(role.name.lower())
            if player:
                player_to_role[player] = role

        if spectator_role == None:
            await send_message_and_file(
                channel=ctx.channel, message=f"Missing spectator role"
            )
            return

        for player in board.players:
            if not player_to_role.get(player):
                await send_message_and_file(
                    channel=ctx.channel,
                    message=f"Missing player role for {player.name}",
                )
                return

        current_cat = cos.pop(0)
        available = 50 - len(current_cat.channels)
        while len(cs) > 0:
            while available == 0:
                current_cat = cos.pop(0)
                available = 50 - len(current_cat.channels)

            assert available > 0

            name, p1, p2 = cs.pop(0)

            overwrites = {
                guild.default_role: PermissionOverwrite(view_channel=False),
                spectator_role: PermissionOverwrite(view_channel=True),
                player_to_role[p1]: PermissionOverwrite(view_channel=True),
                player_to_role[p2]: PermissionOverwrite(view_channel=True),
            }

            await current_cat.create_text_channel(name, overwrites=overwrites)

            available -= 1

    @commands.command(brief="publicize void for chaos")
    async def publicize(self, ctx: commands.Context) -> None:
        if not is_gm(ctx.message.author):
            raise PermissionError(
                f"You cannot publicize a void because you are not a GM."
            )

        channel = ctx.channel
        board = manager.get_board(ctx.guild.id)

        if not board.is_chaos():
            await send_message_and_file(
                channel=channel,
                message="This command only works for chaos games.",
                embed_colour=config.ERROR_COLOUR,
            )

        player = get_player_by_channel(
            channel, manager, ctx.guild.id, ignore_catagory=True
        )

        # TODO hacky
        users = []
        user_permissions: list[tuple[Member, PermissionOverwrite]] = []
        # Find users with access to this channel
        for overwritter, user_permission in channel.overwrites.items():
            if isinstance(overwritter, Member):
                if user_permission.view_channel:
                    users.append(overwritter)
                    user_permissions.append((overwritter, user_permission))

        # TODO don't hardcode
        staff_role = None
        spectator_role = None
        for role in ctx.guild.roles:
            if role.name == "World Chaos Staff":
                staff_role = role
            elif role.name == "Spectators":
                spectator_role = role

        if not staff_role or not spectator_role:
            return

        if not player or len(users) == 0:
            await send_message_and_file(
                channel=ctx.channel,
                message="Can't find the applicable user.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        # Create Thread
        thread: Thread = await channel.create_thread(
            name=f"{player.name.capitalize()} Orders",
            reason=f"Creating Orders for {player.name}",
            invitable=False,
        )
        await thread.send(
            f"{''.join([u.mention for u in users])} | {staff_role.mention}"
        )

        # Allow for sending messages in thread
        for user, permission in user_permissions:
            permission.send_messages_in_threads = True
            await channel.set_permissions(target=user, overwrite=permission)

        # Add spectators
        spectator_permissions = PermissionOverwrite(
            view_channel=True, send_messages=False
        )
        await channel.set_permissions(
            target=spectator_role, overwrite=spectator_permissions
        )

        # Update name
        await channel.edit(name=channel.name.replace("orders", "void"))

        await send_message_and_file(
            channel=channel, message="Finished publicizing void."
        )


async def setup(bot):
    cog = GameManagementCog(bot)
    await bot.add_cog(cog)
