from collections import OrderedDict
import logging
import os
import re

from discord import (
    CategoryChannel,
    Member,
    PermissionOverwrite,
    Role,
    Thread,
)
from discord.ext import commands
from discord.message import convert_emoji_reaction

from bot import config
from bot.parse_edit_state import parse_edit_state
from bot import perms
from bot.utils import (
    get_maps_channel,
    get_orders,
    get_orders_log,
    get_player_by_channel,
    get_role_by_player,
    is_gm,
    log_command,
    send_message_and_file,
    upload_map_to_archive,
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

        message = f"The following categories have been archived: {' '.join([category.name for category in categories])}"
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

        player_categories: list[CategoryChannel] = []
        for c in guild.categories:
            if config.is_player_category(c.name):
                player_categories.append(c)

        if len(player_categories) == 0:
            log_command(logger, ctx, message=f"No player category found")
            await send_message_and_file(
                channel=ctx.channel,
                message="No player category found",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        # ping required players
        pinged_players = 0
        failed_players = []
        response = ""
        for category in player_categories:
            for channel in category.text_channels:
                player = get_player_by_channel(channel, manager, guild.id)
                if player is None:
                    await ctx.send(f"No Player for {channel.name}")
                    continue

                role = get_role_by_player(player, guild.roles)
                if role is None:
                    await ctx.send(f"No Role for {player.name}")
                    continue

                if not board.is_chaos():
                    # Find users which have a player role to not ping spectators
                    users = set(
                        filter(
                            lambda m: len(set(m.roles) & player_roles) > 0, role.members
                        )
                    )
                else:
                    users = set()
                    # Find users with access to this channel
                    for overwritter, permission in channel.overwrites.items():
                        if isinstance(overwritter, Member):
                            if permission.view_channel:
                                users.add(overwritter)
                            pass

                if len(users) == 0:
                    failed_players.append(player)

                    # HACK: ping role in case of no players
                    users.add(role)

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

                    difference = abs(current - count)
                    if difference != 1:
                        order_text = "orders"
                    else:
                        order_text = "order"

                    if has_builds and has_disbands:
                        response = f"Hey {''.join([u.mention for u in users])}, you have both build and disband orders. Please get this looked at."
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
                        if current > available:
                            response = f"Hey {''.join([u.mention for u in users])}, you have {difference} more build {order_text} than possible. Please get this looked at."
                        elif current < available:
                            response = f"Hey {''.join([u.mention for u in users])}, you have {difference} less build {order_text} than necessary. Make sure that you want to waive."
                    elif count < 0:
                        if current < count:
                            response = f"Hey {''.join([u.mention for u in users])}, you have {difference} more disband {order_text} than necessary. Please get this looked at."
                        elif current > count:
                            response = f"Hey {''.join([u.mention for u in users])}, you have {difference} less disband {order_text} than required. Please get this looked at."
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
                    if len(missing) != 1:
                        unit_text = "units"
                    else:
                        unit_text = "unit"

                    if missing:
                        response = f"Hey **{''.join([u.mention for u in users])}**, you are missing moves for the following {len(missing)} {unit_text}:"
                        for unit in sorted(
                            missing, key=lambda _unit: _unit.province.name
                        ):
                            response += f"\n{unit}"

                if response:
                    pinged_players += 1
                    if timestamp:
                        response += f"\n The orders deadline is {timestamp}."
                    await channel.send(response)
                    response = None

        log_command(logger, ctx, message=f"Pinged {pinged_players} players")
        await send_message_and_file(
            channel=ctx.channel, title=f"Pinged {pinged_players} players"
        )

        if len(failed_players) > 0:
            failed_players_str = "\n- ".join([player.name for player in failed_players])
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Failed to find a player for the following:",
                message=f"- {failed_players_str}",
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
        guild = ctx.guild
        if not guild:
            return

        board = manager.get_previous_board(ctx.guild.id)
        curr_board = manager.get_board(guild.id)
        if not board:
            await send_message_and_file(
                channel=ctx.channel,
                title="Failed to get previous phase",
                embed_colour=config.ERROR_COLOUR,
            )
            return
        elif not curr_board:
            await send_message_and_file(
                channel=ctx.channel,
                title="Failed to get current phase",
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

        log = await send_message_and_file(
            channel=orders_log_channel,
            title=f"{board.phase.name} {board.get_year_str()}",
            fields=order_text,
        )
        log_command(logger, ctx, message=f"Successfully published orders")
        await send_message_and_file(
            channel=ctx.channel,
            title=f"Sent Orders to {log.jump_url}",
        )

        # HACK: Lifted from .ping_players
        # Should really work its way into a util function
        roles = {}
        sc_changes = {}
        for player in curr_board.players:
            roles[player.name] = get_role_by_player(player, guild.roles)
            sc_changes[player.name] = len(player.centers)

        for player in board.players:
            sc_changes[player.name] -= len(player.centers)

        sc_changes = [f"  **{role.mention if (role := roles[k]) else k}**: ({'+' if v > 0 else ''}{sc_changes[k]})" for k, v in sorted(sc_changes.items()) if v != 0]
        sc_changes = '\n'.join(sc_changes)

        player_categories: list[CategoryChannel] = []
        for c in guild.categories:
            if config.is_player_category(c.name):
                player_categories.append(c)

        for c in player_categories:
            for ch in c.text_channels:
                player = get_player_by_channel(ch, manager, guild.id)
                if not player or (len(player.units) + len(player.centers) == 0):
                    continue

                role = get_role_by_player(player, guild.roles)
                out = f"Hey **{role.mention if role else player.name}**, the Game has adjudicated!\n"
                await ch.send(out, silent=True)
                await send_message_and_file(
                    channel=ch,
                    title="Adjudication Information",
                    message=(
                        f"**Order Log:** {log.jump_url}\n"
                        f"**From:** {board.phase.name} {board.year + board.year_offset}\n"
                        f"**To:** {curr_board.phase.name} {curr_board.year + board.year_offset}\n"
                        f"**SC Changes:**\n{sc_changes}\n"
                    ),
                )

        if "maps_sas_token" in os.environ:
            file, _ = manager.draw_map_for_board(board, draw_moves=True)
            await upload_map_to_archive(ctx, ctx.guild.id, board, file)

    @commands.command(
        brief="Adjudicates the game and outputs the moves and results maps.",
        description="""
        GMs may append true as an argument to this command to instead get the base svg file.
        * adjudicate {arguments}
        Arguments: 
        * pass true|t|svg|s to return an svg
        * pass standard, dark, blue, or pink for different color modes if present
        * pass test to view maps without doing an actual adjudication
        * pass full to automatically publish orders and maps
        """,
    )
    @perms.gm_only("adjudicate")
    async def adjudicate(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        if not guild:
            return

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
        test_adjudicate = "test" in arguments
        full_adjudicate = "full" in arguments
        movement_adjudicate = "movement" in arguments

        if test_adjudicate and full_adjudicate:
            await send_message_and_file(
                channel=ctx.channel,
                title="Test and full adjudications are incompatable. Defaulting to test adjudication.",
                embed_colour=config.PARTIAL_ERROR_COLOUR,
            )
            full_adjudicate = False

        if full_adjudicate:
            await self.lock_orders(ctx)

        old_turn = (board.get_year_int(), board.phase)
        new_board = manager.adjudicate(ctx.guild.id, test=test_adjudicate)

        log_command(
            logger,
            ctx,
            message=f"Adjudication Successful for {board.phase.name} {board.get_year_str()}",
        )
        file, file_name = manager.draw_map(
            ctx.guild.id,
            draw_moves=True,
            player_restriction=None,
            color_mode=color_mode,
            turn=old_turn,
        )
        title = f"{board.name} — " if board.name else ""
        title += f"{old_turn[1].name} {board.convert_year_int_to_str(old_turn[0])}"
        await send_message_and_file(
            channel=ctx.channel,
            title=f"{title} Orders Map",
            message="Test adjudication" if test_adjudicate else "",
            file=file,
            file_name=file_name,
            convert_svg=return_svg,
        )
        if full_adjudicate:
            map_message = await send_message_and_file(
                channel=get_maps_channel(ctx.guild),
                title=f"{title} Orders Map",
                file=file,
                file_name=file_name,
                convert_svg=True,
            )
        #           await map_message.publish()

        if movement_adjudicate:
            file, file_name = manager.draw_map(
                ctx.guild.id,
                draw_moves=True,
                player_restriction=None,
                color_mode=color_mode,
                turn=old_turn,
                movement_only=True,
            )
            title = f"{board.name} — " if board.name else ""
            title += f"{old_turn[1].name} {old_turn[0]}"
            await send_message_and_file(
                channel=ctx.channel,
                title=f"{title} Movement Map",
                message="Test adjudication" if test_adjudicate else "",
                file=file,
                file_name=file_name,
                convert_svg=return_svg,
            )

        file, file_name = manager.draw_map_for_board(new_board, color_mode=color_mode)
        await send_message_and_file(
            channel=ctx.channel,
            title=f"{title} Results Map",
            message="Test adjudication results" if test_adjudicate else "",
            file=file,
            file_name=file_name,
            convert_svg=return_svg,
        )

        if full_adjudicate:
            map_message = await send_message_and_file(
                channel=get_maps_channel(ctx.guild),
                title=f"{title} Results Map",
                file=file,
                file_name=file_name,
                convert_svg=True,
            )
            #            await map_message.publish()
            await self.publish_orders(ctx)
            await self.unlock_orders(ctx)

        # AUTOMATIC SCOREBOARD OUTPUT FOR DATA SPREADSHEET
        if phase.is_builds(new_board.phase) and (guild.id != config.BOT_DEV_SERVER_ID or guild.name.startswith("Imperial Diplomacy")) and not test_adjudicate:
            channel = self.bot.get_channel(config.IMPDIP_SERVER_WINTER_SCOREBOARD_OUTPUT_CHANNEL_ID)
            if not channel:
                await send_message_and_file(channel=ctx.channel, message="Couldn't automatically send off the Winter Scoreboard data", embed_colour=config.ERROR_COLOUR)
                return
            title = f"### {guild.name} Centre Counts (alphabetical order) | {new_board.phase.name} {new_board.get_year_str()}"

            players = sorted(new_board.players, key=lambda p: p.name)
            counts = "\n".join(map(lambda p: str(len(p.centers)), players))

            await channel.send(title)
            await channel.send(counts)

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
        * .create_player <player_name> <color_code> <win_type> <vscc> <iscc> {extends into the game's history, no starting centres/units}
        * .delete_player <player_name>
        * set_player_points <player_name> <integer>
        * set_player_vassal <liege> <vassal>
        * remove_relationship <player1> <player2>
        * set_game_name <game_name>
        * load_state <server_id> <spring, fall, winter}_{moves, retreats, builds> <year>
        * apocalypse {all OR army, fleet, core, province} !!! deletes everything specified !!!
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
            channel, manager, ctx.guild.id, ignore_category=True
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
