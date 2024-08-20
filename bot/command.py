import random

from discord.ext import commands

from bot.utils import is_gm, is_gm_channel, get_player, is_player_channel
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.order import parse as parse_order

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
    if is_gm(ctx.author):
        if not is_gm_channel(ctx.channel):
            raise PermissionError("You cannot order as a GM in a non-GM channel.")
        return parse_order(ctx.message.content, None, manager, ctx.guild.id)

    player = get_player(ctx.author, manager, ctx.guild.id)
    if player is not None:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError("You cannot order as a player outside of your orders channel.")
        return parse_order(ctx.message.content, player, manager, ctx.guild.id)

    raise PermissionError("You cannot order units because you are neither a GM nor a player.")


def view_orders(ctx: commands.Context, manager: Manager) -> str:
    if is_gm(ctx.author):
        if not is_gm_channel(ctx.channel):
            raise PermissionError("You cannot view orders as a GM in a non-GM channel.")
        return manager.get_moves_map(ctx.guild.id, None)

    player = get_player(ctx.author, manager, ctx.guild.id)
    if player is not None:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError("You cannot view orders as a player outside of your orders channel.")
        return manager.get_moves_map(ctx.guild.id, player)

    raise PermissionError("You cannot view orders because you are neither a GM nor a player.")


def adjudicate(ctx: commands.Context, manager: Manager) -> str:
    if not is_gm(ctx.author):
        raise PermissionError("You cannot adjudicate because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot adjudicate in a non-GM channel.")

    return manager.adjudicate(ctx.guild.id)


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

    build_counts = []
    for player in manager.get_board(ctx.guild.id).players:
        build_counts.append((player.name, len(player.centers) - len(player.units)))
    build_counts = sorted(build_counts, key=lambda counts: counts[1])

    response = ""
    for player, count in build_counts:
        response += f"{player} {count}\n"

    return response


def edit(ctx: commands.Context, _: Manager) -> str:
    if not is_gm(ctx.author):
        raise PermissionError("You cannot edit the game state because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot edit the game state in a non-GM channel.")

    # TODO: (DB) implement edit malleable map state, but not editing constant map features, and return new map
    # TODO: (BETA) allow Admins in hub server in bot channel to edit constant map features
    raise RuntimeError("Edit state has not been implemented yet.")


def create_game(ctx: commands.Context, manager: Manager) -> str:
    if not is_gm(ctx.author):
        raise PermissionError("You cannot create the game because you are not a GM.")

    if not is_gm_channel(ctx.channel):
        raise PermissionError("You cannot create the game in a non-GM channel.")

    return manager.create_game(ctx.guild.id)


# TODO: (BETA) implement new command for inputting new variant
# TODO: (BETA) implement new command for creating game from variant out of choices (more than just Imp Dip)
