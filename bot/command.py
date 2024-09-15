import itertools
import logging
import random

from discord.ext import commands

from bot.parse_edit_state import parse_edit_state
from bot.parse_order import parse_order, parse_remove_order
from bot.utils import is_gm, is_gm_channel, get_player_by_role, is_player_channel, get_orders
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.player import Player

import perms

logger = logging.getLogger(__name__)

ping_text_choices = [
    "proudly states",
    "fervently believes in the power of",
    "is being mind controlled by",
]


def ping(ctx: commands.Context, _: Manager) -> tuple[str, str | None]:
    response = "Beep Boop"
    if random.random() < 0.1:
        author = ctx.message.author
        content = ctx.message.content.removeprefix(".ping")
        if content == "":
            content = " nothing"
        name = author.nick
        if not name:
            name = author.name
        response = name + " " + random.choice(ping_text_choices) + content
    return response, None


def bumble(ctx: commands.Context, _: Manager) -> tuple[str, str | None]:
    word_of_bumble = random.choice(["".join(perm) for perm in itertools.permutations("bumble")])
    if word_of_bumble == "bumble":
        word_of_bumble = "You are the chosen bumble"
    return f"**{word_of_bumble}**", None


async def botsay(ctx: commands.Context) -> None:
    if not is_gm(ctx.message.author) and is_gm_channel(ctx.channel):
        return
    # noinspection PyTypeChecker
    if len(ctx.message.channel_mentions) == 0:
        return
    channel = ctx.message.channel_mentions[0]
    content = ctx.message.content
    content = content.replace(".botsay", "").replace(channel.mention, "").strip()
    if len(content) == 0:
        return
    await ctx.message.add_reaction("👍")
    logger.info(f"{ctx.message.author.name} asked me to say '{content}' in {channel.name}")
    await channel.send(content)


# TODO: (DB) warning cron when in cloud

@perms.player("order")
def order(player: Player | None, ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if player and not board.orders_enabled:
            return "Orders locked! If you think this is an error, contact a GM.", None

    board = manager.get_board(ctx.guild.id)

    return parse_order(ctx.message.content, player, board), None

@perms.player("remove orders")
def remove_order(player: Player | None, ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if player and not board.orders_enabled:
            return "Orders locked! If you think this is an error, contact a GM.", None

    board = manager.get_board(ctx.guild.id)

    return parse_remove_order(ctx.message.content, player, board), None


# TODO: (QOL) GMs want to be able to see orders for a particular player
# TODO: (!) output orders map BUT create something like .orders_log to see it in text like it is here
@perms.player("view orders")
def view_orders(player: Player | None, ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    try:
        order_text = get_orders(manager.get_board(ctx.guild.id), player)
    except RuntimeError as err:
        logger.error(f"View_orders text failed in game with id: {ctx.guild.id}", exc_info=err)
        order_text = "view_orders text failed"
    if player is None:
        try:
            file_name = manager.draw_moves_map(ctx.guild.id, None)
        except Exception as err:
            logger.error(f"View_orders map failed in game with id: {ctx.guild.id}", exc_info=err)
            file_name = None
        return order_text, file_name

    else:
        # file_name = manager.draw_moves_map(ctx.guild.id, player)
        return order_text, None

@perms.gm("adjudicate")
def adjudicate(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    svg_file_name = manager.adjudicate(ctx.guild.id)
    return "Adjudication completed successfully.", svg_file_name  # TODO return file name

@perms.gm("rollback")
def rollback(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    return manager.rollback(ctx.guild.id)

@perms.gm("reload")
def reload(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    return manager.reload(ctx.guild.id)

@perms.gm("remove all orders")
def remove_all(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    for unit in board.units:
        unit.order = None

    database = get_connection()
    database.save_order_for_units(board, board.units)
    return "Successful", None


# TODO: (QOL) this doesn't work right now
# TODO: (QOL) allow players to use this
# TODO: (QOL) include VSCC calculations
@perms.gm("get scoreboard")
def get_scoreboard(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    response = ""
    for player, count in manager.get_board(ctx.guild.id).get_build_counts():
        response += f"{player} {count}\n"

    return response, None

@perms.gm("edit")
def edit(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    # TODO: (BETA) allow Admins in hub server in bot channel to edit constant map features
    return parse_edit_state(ctx.message.content, manager.get_board(ctx.guild.id))

@perms.gm("create a game")
def create_game(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    return manager.create_game(ctx.guild.id), None  # TODO return file name

@perms.gm("unlock orders")
def enable_orders(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = True
    return "Successful", None

@perms.gm("lock orders")
def disable_orders(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = False
    return "Successful", None


def info(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    out = "Phase: " + str(board.phase) + "\nOrders are: " + ("Open" if board.orders_enabled else "Locked")
    return out, None


# TODO: (BETA) implement new command for inputting new variant
# TODO: (BETA) implement new command for creating game from variant out of choices (more than just Imp Dip)
