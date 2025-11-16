import asyncio
import copy
import logging
import os
import random
import time
from typing import Callable
from scipy.integrate import odeint

from black.trans import defaultdict
from discord import (
    CategoryChannel,
    User,
    Member,
    Role,
    HTTPException,
    NotFound,
    TextChannel,
    Thread,
)
from discord import PermissionOverwrite
from discord.ext import commands
from discord.utils import find as discord_find

from bot import config
import bot.perms as perms
from bot.config import IMPDIP_SERVER_ID, IMPDIP_SERVER_SUBSTITUTE_ADVERTISE_CHANNEL_ID, IMPDIP_SERVER_SUBSTITUTE_TICKET_CHANNEL_ID, is_bumble, temporary_bumbles, ERROR_COLOUR, IMPDIP_SERVER_SUBSTITUTE_LOG_CHANNEL_ID
from bot.parse_edit_state import parse_edit_state
from bot.parse_order import parse_order, parse_remove_order
from bot.utils import (
    get_channel_by_player,
    get_filtered_orders,
    get_orders,
    get_orders_log,
    get_player_by_channel,
    get_player_by_name,
    is_gm,
    is_moderator,
    send_message_and_file,
    get_role_by_player,
    log_command,
    fish_pop_model,
)
from diplomacy.adjudicator.utils import svg_to_png
from diplomacy.persistence import phase
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.order import Build, Disband
from diplomacy.persistence.player import Player

import re

from main import bot

logger = logging.getLogger(__name__)

ping_text_choices = [
    "proudly states",
    "fervently believes in the power of",
    "is being mind controlled by",
]
color_options = {"standard", "dark", "pink", "blue", "kingdoms", "empires"}


async def botsay(ctx: commands.Context, _: Manager) -> None:
    # noinspection PyTypeChecker
    if len(ctx.message.channel_mentions) == 0:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="No Channel Given",
            embed_colour=ERROR_COLOUR,
        )
        return
    channel = ctx.message.channel_mentions[0]
    content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
    content = content.replace(channel.mention, "").strip()
    if len(content) == 0:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="No Message Given",
            embed_colour=ERROR_COLOUR,
        )
        return

    message = await send_message_and_file(channel=channel, message=content)
    log_command(logger, ctx, f"Sent Message into #{channel.name}")
    await send_message_and_file(
        channel=ctx.channel,
        title=f"Sent Message",
        message=message.jump_url,
    )


async def announce(ctx: commands.Context, manager: Manager) -> None:
    guilds_with_games = manager.list_servers()
    content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
    content = re.sub(r"<@&[0-9]{16,20}>", r"{}", content)
    roles = list(map(lambda role: role.name, ctx.message.role_mentions))
    message = ""
    for server in ctx.bot.guilds:
        if server is None:
            continue
        admin_chat_channel = next(
            channel for channel in server.channels if is_gm_channel(channel)
        )
        if admin_chat_channel is None:
            message += f"\n- ~~{server.name}~~ Couldn't find admin channel"
            continue

        message += f"\n- {server.name}"
        if server.id in guilds_with_games:
            board = manager.get_board(server.id)
            message += f" - {board.phase.name} {board.get_year_str()}"
        else:
            message += f" - no active game"

        server_roles = []
        for role_name in roles:
            for role in server.roles:
                if role.name == role_name:
                    server_roles.append(role.mention)
                    break
            else:
                server_roles.append(role_name)

        if len(server_roles) > 0:
            await admin_chat_channel.send(
                ("||" + "{}" * len(server_roles) + "||").format(*server_roles)
            )
        await send_message_and_file(
            channel=admin_chat_channel,
            title="Admin Announcement",
            message=content.format(*server_roles),
        )
    log_command(logger, ctx, f"Sent Announcement into {len(ctx.bot.guilds)} servers")
    await send_message_and_file(
        channel=ctx.channel,
        title=f"Announcement sent to {len(ctx.bot.guilds)} servers:",
        message=message,
    )


async def servers(ctx: commands.Context, manager: Manager) -> None:
    servers_with_games = manager.list_servers()
    message = ""
    args = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).split(" ")
    send_id = "id" in args
    send_invite = "invite" in args
    for server in ctx.bot.guilds:
        if server is None:
            continue

        channels = server.channels
        for channel in channels:
            if isinstance(channel, TextChannel):
                break
        else:
            message += f"\n- {server.name} - Could not find a channel for invite"
            continue

        if server.id in servers_with_games:
            servers_with_games.remove(server.id)
            board = manager.get_board(server.id)
            board_state = f" - {board.phase.name} {board.get_year_str()}"
        else:
            board_state = f" - no active game"

        if send_invite:
            try:
                invite = await channel.create_invite(max_age=300)
            except (HTTPException, NotFound):
                message += f"\n- {server.name} - Could not create invite"
            else:
                message += f"\n- [{server.name}](<{invite.url}>)"
        else:
            message += f"\n- {server.name}"

        message += board_state
        if send_id:
            message+= f" - {server.id}"

    # Servers with games the bot is not in
    if servers_with_games:
        message += f"\n There is a further {len(servers_with_games)} games in servers I am no longer in"

    log_command(logger, ctx, f"Found {len(ctx.bot.guilds)} servers")
    await send_message_and_file(
        channel=ctx.channel, title=f"{len(ctx.bot.guilds)} Servers", message=message
    )


async def leave_server(ctx: commands.Context, manager: Manager) -> None:
    leave_id = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
    try:
        leave_id = int(leave_id)
    except ValueError:
        await send_message_and_file(
            channel=ctx.channel,
            title=f"Failed to parse server ID",
            embed_colour=ERROR_COLOUR
        )
        return

    for server in ctx.bot.guilds:
        if server.id == leave_id:
            name = server.name
            # icon = server.icon.url
            try:
                await server.leave()
            except HTTPException:
                await send_message_and_file(
                    channel=ctx.channel,
                    title=f"Failed to leave: {name}",
                    embed_colour=ERROR_COLOUR
                )
            else:
                await send_message_and_file(
                    channel=ctx.channel,
                    title=f"Left Server {name}"
                )
            return
    else:
        await send_message_and_file(
            channel=ctx.channel,
            title=f"Failed to find server",
            embed_colour=ERROR_COLOUR
        )


async def bulk_allocate_role(ctx: commands.Context, manager: Manager) -> None:
    guild = ctx.guild
    if guild is None:
        return

    # extract roles to be allocated based off of mentions
    # .bulk_allocate_role <@B1.4 Player> <@B1.4 GM Team> ...
    roles = ctx.message.role_mentions
    role_names = list(map(lambda r: r.name, roles))

    for role in roles.copy():
        name = role.name.lower()
        if config.is_gm_role(name) or config.is_mod_role(name):
            await send_message_and_file(
                channel=ctx.channel,
                title="Error!",
                embed_color=ERROR_COLOUR,
                message=f"Not allowed to allocate this role using DiploGM: {role.mention}"
            )
            roles.remove(role)
    
    if len(roles) == 0:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="No roles were supplied to allocate. Please include a role mention in the command.",
        )
        return

    # parse usernames from trailing contents
    # .bulk_allocate_role <@B1.4 Player> elisha thisisflare kingofprussia ...
    content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)

    usernames = []
    components = content.split(" ")
    for comp in components:
        if comp == "":
            continue

        match = re.match(r"<@&\d+>", comp)
        if match:
            continue

        usernames.append(comp)

    success_count = 0
    failed = []
    skipped = []
    for user in usernames:
        # FIND USER FROM USERNAME
        member = discord_find(
            lambda m: m.name == user,
            guild.members,
        )

        if not member or member is None:
            failed.append((user, "Member not Found"))
            continue

        for role in roles:
            if role in member.roles:
                skipped.append((user, f"already had role @{role.name}"))
                continue

            try:
                await member.add_roles(role)
                success_count += 1
            except Exception as e:
                failed.append((user, f"Error Adding Role- {e}"))

    failed_out = "\n".join([f"{u}: {m}" for u, m in failed])
    skipped_out = "\n".join([f"{u}: {m}" for u, m in skipped])
    out = (
        f"Allocated Roles {', '.join(role_names)} to {len(usernames)} users.\n"
        + f"Succeeded in applying a role {success_count} times.\n"
        + f"Failed {len(failed)} times.\n"
        + f"Skipped {len(skipped)} times for already having the role.\n"
        + "----\n"
        + f"Failed Reasons:\n{failed_out}\n"
        + "----\n"
        + f"Skipped Reasons:\n{skipped_out}\n"
        + "----\n"
    )

    await send_message_and_file(
        channel=ctx.channel, title="Wave Allocation Info", message=out
    )


@perms.player("order")
async def order(player: Player | None, ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)

    if player and not board.orders_enabled:
        log_command(logger, ctx, f"Orders locked - not processing")
        await send_message_and_file(
            channel=ctx.channel,
            title="Orders locked!",
            message="If you think this is an error, contact a GM.",
            embed_colour=ERROR_COLOUR,
        )
        return

    message = parse_order(ctx.message.content, player, board)
    if "title" in message:
        log_command(logger, ctx, message=message["title"], level=logging.DEBUG)
    elif "message" in message:
        log_command(logger, ctx, message=message["message"][:100], level=logging.DEBUG)
    elif "messages" in message and len(message["messages"]) > 0:
        log_command(logger, ctx, message=message["messages"][0][:100], level=logging.DEBUG)
    await send_message_and_file(channel=ctx.channel, **message)


@perms.player("remove orders")
async def remove_order(
    player: Player | None, ctx: commands.Context, manager: Manager
) -> None:
    board = manager.get_board(ctx.guild.id)

    if player and not board.orders_enabled:
        log_command(logger, ctx, f"Orders locked - not processing")
        await send_message_and_file(
            channel=ctx.channel,
            title="Orders locked!",
            message="If you think this is an error, contact a GM.",
            embed_colour=ERROR_COLOUR,
        )
        return

    content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)

    message = parse_remove_order(content, player, board)
    log_command(logger, ctx, message=message["message"])
    await send_message_and_file(channel=ctx.channel, **message)


@perms.player("view orders")
async def view_orders(
    player: Player | None, ctx: commands.Context, manager: Manager
) -> None:
    arguments = (
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        .strip()
        .lower()
        .split()
    )
    subset = "missing" if {"missing", "miss", "m"} & set(arguments) else None
    subset = (
        "submitted" if {"submitted", "submit", "sub", "s"} & set(arguments) else subset
    )

    try:
        board = manager.get_board(ctx.guild.id)
        order_text = get_orders(board, player, ctx, subset=subset)
    except RuntimeError as err:
        logger.error(err, exc_info=True)
        log_command(
            logger, ctx, message=f"Failed for an unknown reason", level=logging.ERROR
        )
        await send_message_and_file(
            channel=ctx.channel,
            title="Unknown Error: Please contact your local bot dev",
            embed_colour=ERROR_COLOUR,
        )
        return
    log_command(
        logger,
        ctx,
        message=f"Success - generated orders for {board.phase.name} {board.get_year_str()}",
    )
    await send_message_and_file(
        channel=ctx.channel,
        title=f"{board.phase.name} {board.get_year_str()}",
        message=order_text,
    )


async def publish_orders(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_previous_board(ctx.guild.id)
    if not board:
        await send_message_and_file(
            channel=ctx.channel,
            title="Failed to get previous phase",
            embed_colour=ERROR_COLOUR,
        )
        return

    try:
        order_text = get_orders(board, None, ctx, fields=True)
    except RuntimeError as err:
        logger.error(err, exc_info=True)
        log_command(
            logger, ctx, message=f"Failed for an unknown reason", level=logging.ERROR
        )
        await send_message_and_file(
            channel=ctx.channel,
            title="Unknown Error: Please contact your local bot dev",
            embed_colour=ERROR_COLOUR,
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
            embed_colour=ERROR_COLOUR,
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
            channel=ctx.channel, title=f"Sent Orders to {orders_log_channel.mention}"
        )


def parse_season(arguments: list[str, ...], default_year: str) -> tuple[str, phase] | None:
    year, season, retreat = default_year, None, False
    for s in arguments:
        if s.isnumeric() and int(s) > 1640:
            year = s
            
        if s.lower() in ["spring", "s", "sm", "sr"]:
            season = "Spring"
        elif s.lower() in ["fall", "f", "fm", "fr"]:
            season =  "Fall"
        elif s.lower() in ["winter", "w", "wa"]:
            season = "Winter"
        
        if s.lower() in ["retreat", "retreats", "r", "sr", "fr"]:
            retreat = True
            
    if season is None:
        return None
    if season == "Winter":
        parsed_phase = phase.get("Winter Builds")
    else:
        parsed_phase = phase.get(season + " " + ("Retreats" if retreat else "Moves"))
    return (year, parsed_phase)

@perms.player("view map")
async def view_map(
    player: Player | None, ctx: commands.Context, manager: Manager
) -> dict[str, ...]:
    arguments = (
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        .strip()
        .lower()
        .split()
    )
    convert_svg = player or not ({"true", "t", "svg", "s"} & set(arguments))
    color_arguments = list(color_options & set(arguments))
    color_mode = color_arguments[0] if color_arguments else None
    board = manager.get_board(ctx.guild.id)
    season = parse_season(arguments, board.get_year_str())
    
    year = board.get_year_str() if season is None else season[0]
    phase_str = board.phase.name if season is None else season[1].name

    if player and not board.orders_enabled:
        log_command(logger, ctx, f"Orders locked - not processing")
        await send_message_and_file(
            channel=ctx.channel,
            title="Orders locked!",
            message="If you think this is an error, contact a GM.",
            embed_colour=ERROR_COLOUR,
        )
        return

    try:
        if not board.fow:
            file, file_name = manager.draw_moves_map(ctx.guild.id, player, color_mode, season)
        else:
            file, file_name = manager.draw_fow_players_moves_map(
                ctx.guild.id, player, color_mode
            )
    except Exception as err:
        logger.error(err, exc_info=True)
        log_command(
            logger,
            ctx,
            message=f"Failed to generate map for an unknown reason",
            level=logging.ERROR,
        )
        await send_message_and_file(
            channel=ctx.channel,
            title="Unknown Error: Please contact your local bot dev",
            embed_colour=ERROR_COLOUR,
        )
        return
    log_command(
        logger,
        ctx,
        message=f"Generated moves map for {phase_str} {year}",
    )
    await send_message_and_file(
        channel=ctx.channel,
        title=f"{phase_str} {year}",
        file=file,
        file_name=file_name,
        convert_svg=convert_svg,
        file_in_embed=False,
    )


@perms.player("view current")
async def view_current(
    player: Player | None, ctx: commands.Context, manager: Manager
) -> None:
    arguments = (
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        .strip()
        .lower()
        .split()
    )
    convert_svg = not ({"true", "t", "svg", "s"} & set(arguments))
    color_arguments = list(color_options & set(arguments))
    color_mode = color_arguments[0] if color_arguments else None
    board = manager.get_board(ctx.guild.id)
    season = parse_season(arguments, board.get_year_str())
    
    year = board.get_year_str() if season is None else season[0]
    phase_str = board.phase.name if season is None else season[1].name

    if player and not board.orders_enabled:
        log_command(logger, ctx, f"Orders locked - not processing")
        await send_message_and_file(
            channel=ctx.channel,
            title="Orders locked!",
            message="If you think this is an error, contact a GM.",
            embed_colour=ERROR_COLOUR,
        )
        return

    try:
        if not board.fow:
            file, file_name = manager.draw_current_map(ctx.guild.id, color_mode, season)
        else:
            file, file_name = manager.draw_fow_current_map(
                ctx.guild.id, player, color_mode
            )
    except Exception as err:
        logger.error(err, exc_info=True)
        log_command(
            logger,
            ctx,
            message=f"Failed to generate map for an unknown reason",
            level=logging.ERROR,
        )
        await send_message_and_file(
            channel=ctx.channel,
            title="Unknown Error: Please contact your local bot dev",
            embed_colour=ERROR_COLOUR,
        )
        return
    log_command(
        logger,
        ctx,
        message=f"Generated current map for {phase_str} {year}",
    )
    await send_message_and_file(
        channel=ctx.channel,
        title=f"{phase_str} {year}",
        file=file,
        file_name=file_name,
        convert_svg=convert_svg,
        file_in_embed=False,
    )


@perms.player("view gui")
async def view_gui(
    player: Player | None, ctx: commands.Context, manager: Manager
) -> None:
    arguments = (
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        .strip()
        .lower()
        .split()
    )
    color_arguments = list(color_options & set(arguments))
    color_mode = color_arguments[0] if color_arguments else None
    board = manager.get_board(ctx.guild.id)

    if player and not board.orders_enabled:
        log_command(logger, ctx, f"Orders locked - not processing")
        await send_message_and_file(
            channel=ctx.channel,
            title="Orders locked!",
            message="If you think this is an error, contact a GM.",
            embed_colour=ERROR_COLOUR,
        )
        return

    try:
        if not board.fow:
            file, file_name = manager.draw_gui_map(ctx.guild.id, color_mode=color_mode)
        else:
            file, file_name = manager.draw_fow_gui_map(ctx.guild.id, player_restriction=player, color_mode=color_mode)
    except Exception as err:
        log_command(
            logger,
            ctx,
            message=f"Failed to generate map for an unknown reason",
            level=logging.ERROR,
        )
        await send_message_and_file(
            channel=ctx.channel,
            title="Unknown Error: Please contact your local bot dev",
            embed_colour=ERROR_COLOUR,
        )
        raise err
        return
    log_command(
        logger,
        ctx,
        message=f"Generated current map for {board.phase.name} {board.get_year_str()}",
    )
    await send_message_and_file(
        channel=ctx.channel,
        title=f"{board.phase.name} {board.get_year_str()}",
        file=file,
        file_name=file_name,
        convert_svg=False,
        file_in_embed=False,
    )


async def adjudicate(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)

    arguments = (
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        .strip()
        .lower()
        .split()
    )
    return_svg = not ({"true", "t", "svg", "s"} & set(arguments))
    color_arguments = list(color_options & set(arguments))
    color_mode = color_arguments[0] if color_arguments else None
    old_turn = (board.get_year_str(), board.phase)
    # await send_message_and_file(channel=ctx.channel, **await view_map(ctx, manager))
    # await send_message_and_file(channel=ctx.channel, **await view_orders(ctx, manager))
    manager.adjudicate(ctx.guild.id)

    
    log_command(
        logger,
        ctx,
        message=f"Adjudication Successful for {board.phase.name} {board.get_year_str()}",
    )
    file, file_name = manager.draw_moves_map(ctx.guild.id, None, color_mode, old_turn)
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


async def rollback(ctx: commands.Context, manager: Manager) -> None:
    message = manager.rollback(ctx.guild.id)
    log_command(logger, ctx, message=message["message"])
    await send_message_and_file(channel=ctx.channel, **message)


async def reload(ctx: commands.Context, manager: Manager) -> None:
    message = manager.reload(ctx.guild.id)
    log_command(logger, ctx, message=message["message"])
    await send_message_and_file(channel=ctx.channel, **message)


async def remove_all(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)
    for unit in board.units:
        unit.order = None

    database = get_connection()
    database.save_order_for_units(board, board.units)
    log_command(logger, ctx, message="Removed all Orders")
    await send_message_and_file(channel=ctx.channel, title="Removed all Orders")


async def get_scoreboard(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)

    if board.fow:
        perms.assert_gm_only(ctx, "get scoreboard")

    the_player = perms.get_player_by_context(ctx, manager)

    response = ""
    if board.is_chaos() and not "standard" in ctx.message.content:
        scoreboard_rows = []

        latest_index = -1
        latest_points = float("inf")

        for i, player in enumerate(board.get_players_by_points()):
            points = player.points

            if points < latest_points:
                latest_index = i
                latest_points = points

            if i <= 25 or player == the_player:
                scoreboard_rows.append((latest_index + 1, player))
            elif the_player == None:
                break
            elif the_player == player:
                scoreboard_rows.append((latest_index + 1, player))
                break

        index_length = len(str(scoreboard_rows[-1][0]))
        points_length = len(str(scoreboard_rows[0][1]))

        for index, player in scoreboard_rows:
            response += (
                f"\n\\#{index: >{index_length}} | {player.points: <{points_length}} | **{player.name}**: "
                f"{len(player.centers)} ({'+' if len(player.centers) - len(player.units) >= 0 else ''}"
                f"{len(player.centers) - len(player.units)})"
            )
    else:
        response = ""
        for player in board.get_players_by_score():
            if (player_role := get_role_by_player(player, ctx.guild.roles)) is not None:
                player_name = player_role.mention
            else:
                player_name = player.name

            response += (
                f"\n**{player_name}**: "
                f"{len(player.centers)} ({'+' if len(player.centers) - len(player.units) >= 0 else ''}"
                f"{len(player.centers) - len(player.units)}) [{round(player.score() * 100, 1)}%]"
            )

    log_command(logger, ctx, message="Generated scoreboard")
    await send_message_and_file(
        channel=ctx.channel,
        title=f"{board.phase.name}" + " " + f"{board.get_year_str()}",
        message=response,
    )


async def edit(ctx: commands.Context, manager: Manager) -> None:
    edit_commands = ctx.message.content.removeprefix(
        ctx.prefix + ctx.invoked_with
    ).strip()
    message = parse_edit_state(edit_commands, manager.get_board(ctx.guild.id))
    log_command(logger, ctx, message=message["title"])
    await send_message_and_file(channel=ctx.channel, **message)


async def create_game(ctx: commands.Context, manager: Manager) -> None:
    gametype = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
    if gametype == "":
        gametype = "impdip"
    else:
        gametype = gametype.removeprefix(" ")

    message = manager.create_game(ctx.guild.id, gametype)
    log_command(logger, ctx, message=message)
    await send_message_and_file(channel=ctx.channel, message=message)


async def enable_orders(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = True
    log_command(logger, ctx, message="Unlocked orders")
    await send_message_and_file(
        channel=ctx.channel,
        title="Unlocked orders",
        message=f"{board.phase.name} {board.get_year_str()}",
    )


async def disable_orders(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = False
    log_command(logger, ctx, message="Locked orders")
    await send_message_and_file(
        channel=ctx.channel,
        title="Locked orders",
        message=f"{board.phase.name} {board.get_year_str()}",
    )


async def delete_game(ctx: commands.Context, manager: Manager) -> None:
    manager.total_delete(ctx.guild.id)
    log_command(logger, ctx, message=f"Deleted game")
    await send_message_and_file(channel=ctx.channel, title="Deleted game")


async def info(ctx: commands.Context, manager: Manager) -> None:
    try:
        board = manager.get_board(ctx.guild.id)
    except RuntimeError:
        log_command(logger, ctx, message="No game this this server.")
        await send_message_and_file(
            channel=ctx.channel, title="There is no game this this server."
        )
        return
    log_command(
        logger,
        ctx,
        message=f"Displayed info - {board.get_year_str()}|"
        f"{str(board.phase)}|{str(board.datafile)}|"
        f"{'Open' if board.orders_enabled else 'Locked'}",
    )
    await send_message_and_file(
        channel=ctx.channel,
        message=(
            f"Year: {board.get_year_str()}\n"
            f"Phase: {str(board.phase)}\n"
            f"Orders are {'Open' if board.orders_enabled else 'Locked'}\n"
            f"Game Type: {str(board.datafile)}\n"
            f"Chaos: {':white_check_mark:' if board.is_chaos() else ':x:'}\n"
            f"Fog of War: {':white_check_mark:' if board.fow else ':x:'}"
        ),
    )


async def province_info(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)

    if not board.orders_enabled:
        perms.assert_gm_only(
            ctx,
            "You cannot use .province_info in a non-GM channel while orders are locked.",
            non_gm_alt="Orders locked! If you think this is an error, contact a GM.",
        )
        return

    province_name = ctx.message.content.removeprefix(
        ctx.prefix + ctx.invoked_with
    ).strip()
    if not province_name:
        log_command(logger, ctx, message=f"No province given")
        await send_message_and_file(
            channel=ctx.channel,
            title="No province given",
            message="Usage: .province_info <province>",
        )
        return
    try:
        province, coast = board.get_province_and_coast(province_name)
    except:
        log_command(logger, ctx, message=f"Province `{province_name}` not found")
        await send_message_and_file(
            channel=ctx.channel, title=f"Could not find province {province_name}"
        )
        return

    # FOW permissions
    if board.fow:
        player = perms.require_player_by_context(ctx, manager, "get province info")
        if player and not province in board.get_visible_provinces(player):
            log_command(
                logger,
                ctx,
                message=f"Province `{province_name}` hidden by fow to player",
            )
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Province {province.name} is not visible to you",
            )
            return

    # fmt: off
    if not coast:
        out = f"Type: {province.type.name}\n" + \
            f"Coasts: {len(province.coasts)}\n" + \
            f"Owner: {province.owner.name if province.owner else 'None'}\n" + \
            f"Unit: {(province.unit.player.name + ' ' + province.unit.unit_type.name) if province.unit else 'None'}\n" + \
            f"Center: {province.has_supply_center}\n" + \
            f"Core: {province.core.name if province.core else 'None'}\n" + \
            f"Half-Core: {province.half_core.name if province.half_core else 'None'}\n" + \
            f"Adjacent Provinces:\n- " + "\n- ".join(sorted([adjacent.name for adjacent in province.adjacent | province.impassible_adjacent])) + "\n"
    else:
        coast_unit = None
        if province.unit and province.unit.coast == coast:
            coast_unit = province.unit

        out = "Type: COAST\n" + \
            f"Coast Unit: {(coast_unit.player.name + ' ' + coast_unit.unit_type.name) if coast_unit else 'None'}\n" + \
            f"Province Unit: {(province.unit.player.name + ' ' + province.unit.unit_type.name) if province.unit else 'None'}\n" + \
            "Adjacent Provinces:\n" + \
            "- " + \
            "\n- ".join(sorted([adjacent.name for adjacent in coast.get_adjacent_locations()])) + "\n"
    # fmt: on
    log_command(logger, ctx, message=f"Got info for {province_name}")

    # FIXME title should probably include what coast it is.
    await send_message_and_file(channel=ctx.channel, title=province.name, message=out)


async def player_info(ctx: commands.Context, manager: Manager) -> None:
    guild = ctx.guild
    if not guild:
        return

    board = manager.get_board(guild.id)

    if not board.orders_enabled:
        perms.assert_gm_only(
            ctx,
            "You cannot use .player_info in a non-GM channel while orders are locked.",
            non_gm_alt="Orders locked! If you think this is an error, contact a GM.",
        )
        return

    player_name = ctx.message.content.removeprefix(
        ctx.prefix + ctx.invoked_with
    ).strip()
    if not player_name:
        log_command(logger, ctx, message=f"No player given")
        await send_message_and_file(
            channel=ctx.channel,
            title="No player given",
            message="Usage: .player_info <player>",
        )
        return

    variant = "standard"
    player: Player | None = None
    if board.is_chaos():
        # HACK: chaos has same name of players as provinces so we exploit that
        province, _ = board.get_province_and_coast(player_name)
        player = board.get_player(province.name.lower())
        variant = "chaos"
            
    elif board.fow:
        await send_message_and_file(
            channel=ctx.channel, title=f"Gametype Error!", message="This command does not work with FoW", embed_colour=ERROR_COLOUR
        )
        return

    else:
        try:
            player = board.get_player(player_name)
        except ValueError:
            player = None

    # f"Initial/Current/Victory SC Count [Score]: {player.iscc}/{len(player.centers)}/{player.vscc} [{player.score()}%]\n" + \

    if player is None:
        log_command(logger, ctx, message=f"Player `{player}` not found")
        await send_message_and_file(
            channel=ctx.channel, title=f"Could not find player {player_name}"
        )
        return

    out = player.info(variant)
    log_command(logger, ctx, message=f"Got info for player {player}")

    # FIXME title should probably include what coast it is.
    await send_message_and_file(channel=ctx.channel, title=player.name, message=out)


@perms.player("view visible provinces")
async def visible_provinces(
    player: Player | None, ctx: commands.Context, manager: Manager
) -> None:
    board = manager.get_board(ctx.guild.id)

    if not player or not board.fow:
        log_command(logger, ctx, message=f"No fog of war game")
        await send_message_and_file(
            channel=ctx.channel,
            message="This command only works for players in fog of war games.",
            embed_colour=ERROR_COLOUR,
        )
        return

    visible_provinces = board.get_visible_provinces(player)
    log_command(
        logger, ctx, message=f"There are {len(visible_provinces)} visible provinces"
    )
    await send_message_and_file(
        channel=ctx.channel, message=", ".join([x.name for x in visible_provinces])
    )
    return


async def publicize(ctx: commands.Context, manager: Manager) -> None:
    if not is_gm(ctx.message.author):
        raise PermissionError(f"You cannot publicize a void because you are not a GM.")

    channel = ctx.channel
    board = manager.get_board(ctx.guild.id)

    if not board.is_chaos():
        await send_message_and_file(
            channel=channel,
            message="This command only works for chaos games.",
            embed_colour=ERROR_COLOUR,
        )

    player = get_player_by_channel(channel, manager, ctx.guild.id, ignore_category=True)

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
            embed_colour=ERROR_COLOUR,
        )
        return

    # Create Thread
    thread: Thread = await channel.create_thread(
        name=f"{player.name.capitalize()} Orders",
        reason=f"Creating Orders for {player.name}",
        invitable=False,
    )
    await thread.send(f"{''.join([u.mention for u in users])} | {staff_role.mention}")

    # Allow for sending messages in thread
    for user, permission in user_permissions:
        permission.send_messages_in_threads = True
        await channel.set_permissions(target=user, overwrite=permission)

    # Add spectators
    spectator_permissions = PermissionOverwrite(view_channel=True, send_messages=False)
    await channel.set_permissions(
        target=spectator_role, overwrite=spectator_permissions
    )

    # Update name
    await channel.edit(name=channel.name.replace("orders", "void"))

    await send_message_and_file(channel=channel, message="Finished publicizing void.")


async def all_province_data(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)

    if not board.orders_enabled:
        perms.assert_gm_only(ctx, "call .all_province_data while orders are locked")

    province_by_owner = defaultdict(list)
    for province in board.provinces:
        owner = province.owner
        if not owner:
            owner = None
        province_by_owner[owner].append(province.name)

    message = ""
    for owner, provinces in province_by_owner.items():
        if owner is None:
            player_name = "None"
        elif (player_role := get_role_by_player(owner, ctx.guild.roles)) is not None:
            player_name = player_role.mention
        else:
            player_name = owner

        message += f"{player_name}: "
        for province in provinces:
            message += f"{province}, "
        message += "\n\n"

    log_command(
        logger,
        ctx,
        message=f"Found {sum(map(len, province_by_owner.values()))} provinces",
    )
    await send_message_and_file(channel=ctx.channel, message=message)


# needed due to async
from bot.utils import is_gm_channel


# for fog of war
async def publish_fow_current(ctx: commands.Context, manager: Manager):
    await publish_map(
        ctx, manager, "starting map", lambda m, s, p: m.draw_fow_current_map(s, p)
    )


async def publish_fow_moves(
    ctx: commands.Context,
    manager: Manager,
):
    board = manager.get_board(ctx.guild.id)

    if not board.fow:
        raise ValueError("This is not a fog of war game")

    filter_player = board.get_player(
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip()
    )

    await publish_map(
        ctx,
        manager,
        "moves map",
        lambda m, s, p: m.draw_fow_moves_map(s, p),
        filter_player,
    )


# FIXME add a decorator / helper method for iterating over all player order channels
async def publish_map(
    ctx: commands.Context,
    manager: Manager,
    name: str,
    map_caller: Callable[[Manager, int, Player], tuple[str, str]],
    filter_player=None,
):
    player_category = None

    guild = ctx.guild
    guild_id = guild.id
    board = manager.get_board(guild_id)

    for category in guild.categories:
        if config.is_player_category(category.name):
            player_category = category
            break

    if not player_category:
        # FIXME this shouldn't be an Error/this should propagate
        raise RuntimeError("No player category found")

    name_to_player: dict[str, Player] = {}
    for player in board.players:
        name_to_player[player.name.lower()] = player

    tasks = []

    for channel in player_category.channels:
        player = get_player_by_channel(channel, manager, guild.id)

        if not player or (filter_player and player != filter_player):
            continue

        message = f"Here is the {name} for {board.get_year_str()} {board.phase.name}"
        # capture local of player
        tasks.append(
            map_publish_task(
                lambda player=player: map_caller(manager, guild_id, player),
                channel,
                message,
            )
        )

    await asyncio.gather(*tasks)


# if possible save one svg slot for others
fow_export_limit = asyncio.Semaphore(
    max(int(config.SIMULATRANEOUS_SVG_EXPORT_LIMIT) - 1, 1)
)


async def map_publish_task(map_maker, channel, message):
    async with fow_export_limit:
        file, file_name = map_maker()
        file, file_name = await svg_to_png(file, file_name)
        await send_message_and_file(
            channel=channel,
            message=message,
            file=file,
            file_name=file_name,
            file_in_embed=False,
        )


async def publish_fow_order_logs(ctx: commands.Context, manager: Manager):
    player_category = None

    guild = ctx.guild
    guild_id = guild.id
    board = manager.get_board(guild_id)

    if not board.fow:
        raise ValueError("This is not a fog of war game")

    filter_player = board.get_player(
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip()
    )

    for category in guild.categories:
        if config.is_player_category(category.name):
            player_category = category
            break

    if not player_category:
        return "No player category found"

    name_to_player: dict[str, Player] = {}
    for player in board.players:
        name_to_player[player.name.lower()] = player

    for channel in player_category.channels:
        player = get_player_by_channel(channel, manager, guild.id)

        if not player or (filter_player and player != filter_player):
            continue

        message = get_filtered_orders(board, player)

        await send_message_and_file(channel=channel, message=message)

    return "Successful"


async def ping_players(ctx: commands.Context, manager: Manager) -> None:
    player_categories: list[CategoryChannel] = []

    timestamp = re.match(
        r"<t:(\d+):[a-zA-Z]>",
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip(),
    )
    if timestamp:
        timestamp = f"<t:{timestamp.group(1)}:R>"

    guild = ctx.guild
    guild_id = guild.id
    board = manager.get_board(guild_id)

    for category in guild.categories:
        # TODO hacky
        if config.is_player_category(category.name) or (
            board.is_chaos() and "Order" in category.name
        ):
            player_categories.append(category)

    if len(player_categories) == 0:
        log_command(logger, ctx, message=f"No player category found")
        await send_message_and_file(
            channel=ctx.channel,
            message="No player category found",
            embed_colour=ERROR_COLOUR,
        )
        return

    # find player roles
    if not board.is_chaos():
        name_to_player: dict[str, Player] = dict()
        player_to_role: dict[Player | None, Role] = dict()
        for player in board.players:
            name_to_player[player.name.lower()] = player

        player_roles: set[Role] = set()

        for role in guild.roles:
            if config.is_player_role(role.name):
                player_roles.add(role)

            player = name_to_player.get(role.name.lower())
            if player:
                player_to_role[player] = role

        if len(player_roles) == 0:
            log_command(logger, ctx, message=f"No player role found")
            await send_message_and_file(
                channel=ctx.channel,
                message="No player role found",
                embed_colour=ERROR_COLOUR,
            )
            return

    response = None
    pinged_players = 0
    failed_players = []

    for player_category in player_categories:
        for channel in player_category.channels:
            player = get_player_by_channel(
                channel, manager, guild.id, ignore_category=board.is_chaos()
            )

            if not player:
                await send_message_and_file(
                    channel=ctx.channel, title=f"Couldn't find player for {channel}"
                )
                continue

            if not board.is_chaos():
                role = player_to_role.get(player)
                if not role:
                    log_command(
                        logger,
                        ctx,
                        message=f"Missing player role for player {player.name} in guild {guild_id}",
                        level=logging.WARN,
                    )
                    continue

                # Find users which have a player role to not ping spectators
                users = set(
                    filter(lambda m: len(set(m.roles) & player_roles) > 0, role.members)
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
                continue

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
                    for unit in sorted(missing, key=lambda _unit: _unit.province.name):
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
        await send_message_and_file(
            channel=ctx.channel,
            title=f"Failed to find the following players: {','.join([player.name for player in failed_players])}",
        )


async def archive(ctx: commands.Context, _: Manager) -> None:
    categories = [channel.category for channel in ctx.message.channel_mentions]
    if not categories:
        await send_message_and_file(
            channel=ctx.channel,
            message="This channel is not part of a category.",
            embed_colour=ERROR_COLOUR,
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


async def blitz(ctx: commands.Context, manager: Manager) -> None:
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
                channel=ctx.channel, message=f"Missing player role for {player.name}"
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


async def wipe(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)
    cs = []
    pla = sorted(board.players, key=lambda p: p.name)
    for p1 in pla:
        for p2 in pla:
            if p1.name < p2.name:
                c = f"{p1.name}-{p2.name}"
                cs.append(c.lower())

    guild = ctx.guild

    for channel in guild.channels:
        if channel.name in cs:
            await channel.delete()


async def nick(ctx: commands.Context, manager: Manager) -> None:
    name: str = ctx.author.nick
    if name == None:
        name = ctx.author.name
    if "]" in name:
        prefix = name.split("] ", 1)[0]
        prefix = prefix + "] "
    else:
        prefix = ""
    name = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip()
    if name == "":
        await send_message_and_file(
            channel=ctx.channel,
            embed_colour=ERROR_COLOUR,
            message=f"A nickname must be at least 1 character",
        )
        return
    if len(prefix + name) > 32:
        await send_message_and_file(
            channel=ctx.channel,
            embed_colour=ERROR_COLOUR,
            message=f"A nickname must be at less than 32 total characters.\n Yours is {len(prefix + name)}",
        )
        return
    await ctx.author.edit(nick=prefix + name)
    await send_message_and_file(
        channel=ctx.channel, message=f"Nickname updated to `{prefix + name}`"
    )


async def record_spec(ctx: commands.Context, manager: Manager) -> None:
    guild = ctx.guild
    if not guild:
        return

    if len(ctx.message.role_mentions) == 0:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Did not mention a nation.",
            embed_colour=ERROR_COLOUR,
        )
        return

    if len(ctx.message.mentions) == 0:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Did not mention a user.",
            embed_colour=ERROR_COLOUR,
        )
        return

    user = ctx.message.mentions[0]
    user_id = user.id

    power_role = ctx.message.role_mentions[0]
    power_id = power_role.id

    out = manager.save_spec_request(guild.id, user_id, power_id, override=True)
    await send_message_and_file(channel=ctx.channel, message=out)


async def backlog_specs(ctx: commands.Context, manager: Manager) -> None:
    guild = ctx.guild
    if not guild:
        return

    cspec = discord_find(lambda r: r.name == "Country Spectator", guild.roles)
    if cspec is None:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="There is no Country Spectator role in this server.",
        )
        return

    out = ""
    for member in guild.members:
        if cspec not in member.roles:
            continue

        power_role = None
        for role in member.roles:
            if discord_find(
                lambda c: c.name == f"{role.name.lower()}-orders", guild.text_channels
            ):
                power_role = role
                break

        if power_role is None:
            continue

        result = manager.save_spec_request(guild.id, member.id, power_role.id)
        out += f"{member.mention} -> {power_role.mention}: {result}\n"

    await send_message_and_file(
        channel=ctx.channel, title="Spectator Backlog Results", message=out
    )


async def membership(ctx: commands.Context, _: Manager, user: User) -> None:
    guild = ctx.guild
    if not guild:
        return

    out = f"""
User: {user.mention} [{user.name}]
Number of Mutual Servers: {len(user.mutual_guilds)}
----
"""

    for shared in sorted(user.mutual_guilds, key=lambda g: g.name):
        out += f"{shared.name}\n"

    await send_message_and_file(
        channel=ctx.channel, title=f"User Membership Results", message=out
    )

async def advertise(ctx: commands.Context, manager: Manager, power_role: Role, timestamp: str | None = None, message: str = "No message given."):
    guild = ctx.guild
    if not guild:
        return

    _hub = ctx.bot.get_guild(IMPDIP_SERVER_ID)
    if not _hub:
        raise perms.CommandPermissionError("Can't advertise as can't access the Imperial Diplomacy Hub Server.")
    
    interested_sub_ping = ""
    interested_sub_role = discord_find(lambda r: r.name == "Interested Substitute", _hub.roles)
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
            embed_colour=ERROR_COLOUR,
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

    sub_period = "Permanent" if timestamp is None else f"Temporary until {timestamp}"

    # GET CHANNELS FOR POST / REDIRECTS
    ticket_channel = ctx.bot.get_channel(IMPDIP_SERVER_SUBSTITUTE_TICKET_CHANNEL_ID)
    if not ticket_channel:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Could not find the channel where substitute tickets can be created",
            embed_colour=ERROR_COLOUR,
        )
        return
    
    advertise_channel = ctx.bot.get_channel(IMPDIP_SERVER_SUBSTITUTE_ADVERTISE_CHANNEL_ID)
    if not advertise_channel:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Could not find the channel meant for advertisements",
            embed_colour=ERROR_COLOUR,
        )
        return

    title= f"Substitute Advertisement"
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

async def substitute(
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
            embed_colour=ERROR_COLOUR,
        )
        return

    in_member = guild.get_member(in_user.id)
    if not in_member:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Can't substitute a player that is not in the server!",
            embed_colour=ERROR_COLOUR,
        )
        return

    if not get_player_by_name(power_role.name, manager, guild.id):
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Did not supply a Player role.",
            embed_colour=ERROR_COLOUR,
        )
        return

    # fetch relevant roles to swap around on the users
    player_role = discord_find(lambda r: r.name == "Player", guild.roles)
    if not player_role:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Can't proceed with automatic substitution processing: Couldn't find 'Player' role.",
            embed_colour=ERROR_COLOUR,
        )
        return
    
    orders_role = discord_find(lambda r: r.name == f"orders-{power_role.name.lower()}", guild.roles)
    if not orders_role:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message=f"Can't proceed with automatic substitution processing: Couldn't find 'orders-{power_role.name.lower()}' role.",
            embed_colour=ERROR_COLOUR,
        )
        return

    cspec_role = discord_find(lambda r: r.name == "Country Spectator", guild.roles)
    if not cspec_role:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Can't proceed with automatic substitution processing: Couldn't find 'Country Spectator' role.",
            embed_colour=ERROR_COLOUR,
        )
        return
    

    # if incoming is currently a player
    if player_role in in_member.roles and power_role not in in_member.roles:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Can't substitute in a current player for another power!",
            embed_colour=ERROR_COLOUR,
        )
        return

    # if incoming is a country spec but not of current player
    if cspec_role in in_member.roles and power_role not in in_member.roles:
        await send_message_and_file(
            channel=ctx.channel,
            title="Error",
            message="Incoming player is a country spectator for another power!",
            embed_colour=ERROR_COLOUR,
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
                embed_colour=ERROR_COLOUR,
            )
            return


    # log a substitution is occurring in the gm space
    # TODO: Update Substitution Logging to include Reputation after Bot Integration
    logc = ctx.bot.get_channel(IMPDIP_SERVER_SUBSTITUTE_LOG_CHANNEL_ID)
    out = (
        f"Game: {guild.name}\n" 
        + f"- Guild ID: {guild.id}\n"
        + f"In: {in_user.mention}[{in_user.name}]\n"
        + f"Out: {out_user.mention}[{out_user.name}]\n"
        + f"Phase: {board.phase.name} {board.get_year_str()}\n"
        + f"Reason: {reason}"
    )
    await send_message_and_file(channel=logc, message=out)
    await send_message_and_file(channel=ctx.channel, message="Recorded substitution in #reputation-tracker.")

    # log to server specific sub-tracking channel
    sub_tracker_channel = discord_find(lambda c: c.name == "player-sub-tracking", guild.text_channels)
    if sub_tracker_channel:
        await send_message_and_file(channel=sub_tracker_channel, message=out)
    else:
        await ctx.send("Could not find #player-sub-tracking channel, logging message here instead")
        await send_message_and_file(channel=ctx.channel, message=out)

    # PROCESS ROLE ASSIGNMENTS
    out = f"Outgoing Player: {out_user.name}\n"
    out_member = guild.get_member(out_user.id)
    if out_member:
        prev_roles = list(filter(lambda r: r in out_member.roles, [player_role, orders_role])) # roles to remove if they exist
        prev_role_names = ", ".join(map(lambda r: r.mention, prev_roles))
        out += f"- Previous Roles: {prev_role_names}\n"
        
        new_roles = [cspec_role] # roles to add
        new_role_names = ", ".join(map(lambda r: r.mention, new_roles)) 
        out += f"- New Roles: {new_role_names}\n"

        try:
            await out_member.remove_roles(*prev_roles, reason="Substitution")
            await out_member.add_roles(*new_roles)
        except HTTPException:
            out += f"[ERROR] Failed to swap roles for outgoing player: {out_user.name}\n"

    out += f"Incoming Player: {in_user.name}\n"
    prev_roles = list(filter(lambda r: r in in_member.roles, [cspec_role])) # roles to remove if they exist
    prev_role_names = ", ".join(map(lambda r: r.mention, prev_roles))
    out += f"- Previous Roles: {prev_role_names}\n"

    new_roles = [player_role, power_role, orders_role] # roles to add
    new_role_names = ", ".join(map(lambda r: r.mention, new_roles))
    out += f"- New Roles: {new_role_names}\n"
    
    try:
        await in_member.remove_roles(*prev_roles, reason="Substitution")
        await in_member.add_roles(*new_roles)
    except HTTPException:
        out += f"[ERROR] Failed to swap roles for incoming player: {in_user.name}"

    await send_message_and_file(channel=ctx.channel, title="Substitution results", message=out)


class ContainedPrinter:
    def __init__(self):
        self.text = ""

    def __call__(self, *args):
        self.text += " ".join(map(str, args)) + "\n"


async def exec_py(ctx: commands.Context, manager: Manager) -> None:
    board = manager.get_board(ctx.guild.id)
    code = (
        ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        .strip()
        .strip("`")
    )

    embed_print = ContainedPrinter()

    try:
        exec(code, {"print": embed_print, "board": board})
    except Exception as e:
        embed_print("\n" + repr(e))

    if embed_print.text:
        await send_message_and_file(channel=ctx.channel, message=embed_print.text)
    manager._database.delete_board(board)

    manager._database.save_board(ctx.guild.id, board)
