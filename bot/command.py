import logging
import random

from discord.ext import commands

from bot.parse_edit_state import parse_edit_state
from bot.parse_order import parse_order, parse_remove_order
from bot.utils import is_gm, is_gm_channel, get_player_by_role, is_player_channel, get_orders
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.db.database import get_connection

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


# TODO: (DB) warning cron when in cloud
def order(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)

    if not board.orders_enabled:
        return "Orders locked! If you think this is an error, contact a GM.", None

    if is_gm(ctx.message.author):
        if not is_gm_channel(ctx.channel):
            raise PermissionError("You cannot order as a GM in a non-GM channel.")
        return parse_order(ctx.message.content, None, board), None

    player = get_player_by_role(ctx.message.author, manager, ctx.guild.id)
    if player is not None:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError("You cannot order as a player outside of your orders channel.")
        return parse_order(ctx.message.content, player, board), None

    raise PermissionError("You cannot order units because you are neither a GM nor a player.")


def remove_order(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)

    if not board.orders_enabled:
        return "Orders locked! If you think this is an error, contact a GM.", None

    if is_gm(ctx.message.author):
        if not is_gm_channel(ctx.channel):
            raise PermissionError("You cannot remove orders as a GM in a non-GM channel.")
        return parse_remove_order(ctx.message.content, None, board), None

    player = get_player_by_role(ctx.message.author, manager, ctx.guild.id)
    if player is not None:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError("You cannot remove orders as a player outside of your orders channel.")
        return parse_remove_order(ctx.message.content, player, board), None

    raise PermissionError("You cannot remove orders because you are neither a GM nor a player.")


# TODO: (!) output orders map BUT create something like .orders_log to see it in text like it is here
def view_orders(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if is_gm(ctx.message.author):
        if not is_gm_channel(ctx.channel):
            raise PermissionError("You cannot view orders as a GM in a non-GM channel.")

        try:
            order_text = get_orders(manager.get_board(ctx.guild.id), None)
        except:
            logger.error(f"View_orders text failed in game with id: {ctx.guild.id}")
            order_text = "view_orders text failed"

        try:
            file_name = manager.draw_moves_map(ctx.guild.id, None)
        except:
            logger.error(f"View_orders map failed in game with id: {ctx.guild.id}")
            file_name = None

        return order_text, file_name

    player = get_player_by_role(ctx.message.author, manager, ctx.guild.id)
    if player is not None:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError("You cannot view orders as a player outside of your orders channel.")
        # file_name = manager.draw_moves_map(ctx.guild.id, player)
        return get_orders(manager.get_board(ctx.guild.id), player), None

    raise PermissionError("You cannot view orders because you are neither a GM nor a player.")


def adjudicate(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if not is_gm(ctx.message.author):
        raise PermissionError("You cannot adjudicate because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot adjudicate in a non-GM channel.")

    svg_file_name = manager.adjudicate(ctx.guild.id)
    return "Adjudication completed successfully.", svg_file_name  # TODO return file name


def rollback(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if not is_gm(ctx.message.author):
        raise PermissionError("You cannot rollback because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot rollback in a non-GM channel.")

    return manager.rollback(), None  # TODO return file name


def remove_all(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if not is_gm(ctx.message.author):
        raise PermissionError("You cannot modify all orders because you are not a GM.")
    if not is_gm_channel(ctx.message.author):
        raise PermissionError("You cannot remove orders in a non-GM channel.")

    board = manager.get_board(ctx.guild.id)
    for unit in board.units:
        unit.order = None

    database = get_connection()
    database.save_order_for_units(board, board.units)
    return "Successful", None


# TODO: (QOL) this doesn't work right now
# TODO: (QOL) allow players to use this
# TODO: (QOL) include VSCC calculations
def get_scoreboard(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if not is_gm(ctx.message.author):
        raise PermissionError("You cannot get the scoreboard because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot get the scoreboard in a non-GM channel.")

    response = ""
    for player, count in manager.get_board(ctx.guild.id).get_build_counts():
        response += f"{player} {count}\n"

    return response, None


def edit(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    # TODO: (BETA) allow Admins in hub server in bot channel to edit constant map features
    if not is_gm(ctx.message.author):
        raise PermissionError("You cannot edit the game state because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot edit the game state in a non-GM channel.")

    return parse_edit_state(ctx.message.content, manager.get_board(ctx.guild.id))


def create_game(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if not is_gm(ctx.message.author):
        raise PermissionError("You cannot create the game because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot create the game in a non-GM channel.")

    return manager.create_game(ctx.guild.id), None  # TODO return file name


def enable_orders(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if not is_gm(ctx.message.author):
        raise PermissionError("You cannot create the game because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot create the game in a non-GM channel.")

    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = True
    return "Successful", None


def disable_orders(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    if not is_gm(ctx.message.author):
        raise PermissionError("You cannot create the game because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot create the game in a non-GM channel.")

    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = False
    return "Successful", None


# TODO: (BETA) implement new command for inputting new variant
# TODO: (BETA) implement new command for creating game from variant out of choices (more than just Imp Dip)
