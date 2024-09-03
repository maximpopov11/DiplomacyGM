import random

from discord.ext import commands

from bot.parse_edit_state import parse_edit_state
from bot.parse_order import parse_order, parse_remove_order
from bot.utils import is_gm, is_gm_channel, get_player_by_role, is_player_channel, get_orders
from diplomacy.persistence.manager import Manager

ping_text_choices = [
    "proudly states",
    "fervently believes in the power of",
    "is being mind controlled by",
]


def ping(ctx: commands.Context, _: Manager) -> str:
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
    return response


def order(ctx: commands.Context, manager: Manager) -> str:
    board = manager.get_board(ctx.guild.id)

    if is_gm(ctx.author):
        if not is_gm_channel(ctx.channel):
            raise PermissionError("You cannot order as a GM in a non-GM channel.")
        return parse_order(ctx.message.content, None, board)

    player = get_player_by_role(ctx.author, manager, ctx.guild.id)
    if player is not None:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError("You cannot order as a player outside of your orders channel.")
        return parse_order(ctx.message.content, player, board)

    raise PermissionError("You cannot order units because you are neither a GM nor a player.")


def remove_order(ctx: commands.Context, manager: Manager) -> str:
    board = manager.get_board(ctx.guild.id)

    if is_gm(ctx.author):
        if not is_gm_channel(ctx.channel):
            raise PermissionError("You cannot remove orders as a GM in a non-GM channel.")
        return parse_remove_order(ctx.message.content, None, board)

    player = get_player_by_role(ctx.author, manager, ctx.guild.id)
    if player is not None:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError("You cannot remove orders as a player outside of your orders channel.")
        return parse_remove_order(ctx.message.content, player, board)

    raise PermissionError("You cannot remove orders because you are neither a GM nor a player.")


# TODO: (DB) output orders map
def view_orders(ctx: commands.Context, manager: Manager) -> str:
    if is_gm(ctx.author):
        if not is_gm_channel(ctx.channel):
            raise PermissionError("You cannot view orders as a GM in a non-GM channel.")
        return get_orders(manager.get_board(ctx.guild.id), None)
        # return manager.draw_moves_map(ctx.guild.id, None)

    player = get_player_by_role(ctx.author, manager, ctx.guild.id)
    if player is not None:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError("You cannot view orders as a player outside of your orders channel.")
        return get_orders(manager.get_board(ctx.guild.id), player)
        # return manager.draw_moves_map(ctx.guild.id, player)

    raise PermissionError("You cannot view orders because you are neither a GM nor a player.")


def adjudicate(ctx: commands.Context, manager: Manager) -> str:
    if not is_gm(ctx.author):
        raise PermissionError("You cannot adjudicate because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot adjudicate in a non-GM channel.")

    manager.adjudicate(ctx.guild.id)
    return "Adjudication completed successfully."


def rollback(ctx: commands.Context, manager: Manager) -> str:
    if not is_gm(ctx.author):
        raise PermissionError("You cannot rollback because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot rollback in a non-GM channel.")

    return manager.rollback()


def get_scoreboard(ctx: commands.Context, manager: Manager) -> str:
    if not is_gm(ctx.author):
        raise PermissionError("You cannot get the scoreboard because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot get the scoreboard in a non-GM channel.")

    response = ""
    for player, count in manager.get_board(ctx.guild.id).get_build_counts():
        response += f"{player} {count}\n"

    return response


def edit(ctx: commands.Context, manager: Manager) -> str:
    # TODO: (BETA) allow Admins in hub server in bot channel to edit constant map features
    if not is_gm(ctx.author):
        raise PermissionError("You cannot edit the game state because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot edit the game state in a non-GM channel.")

    return parse_edit_state(ctx.message.content, manager.get_board(ctx.guild.id))


def create_game(ctx: commands.Context, manager: Manager) -> str:
    if not is_gm(ctx.author):
        raise PermissionError("You cannot create the game because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot create the game in a non-GM channel.")

    return manager.create_game(ctx.guild.id)


# TODO: (BETA) implement new command for inputting new variant
# TODO: (BETA) implement new command for creating game from variant out of choices (more than just Imp Dip)
