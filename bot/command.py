import random
from typing import Optional

from discord.ext import commands

import bot.utils as utils
import diplomacy.order
from diplomacy.board.vector.vector import parse as parse_board
from diplomacy.persistence.adjudicator import Adjudicator

adjudicator: Optional[Adjudicator] = None

ping_text_choices = [
    "proudly states",
    "fervently believes in the power of",
    "is being mind controlled by",
]


def ping(ctx: commands.Context) -> str:
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


def order(ctx: commands.Context) -> str:
    if utils.is_gm(ctx.author):
        if not utils.is_gm_channel(ctx.channel):
            raise RuntimeError("You cannot order as a GM in a non-GM channel.")
        return diplomacy.order.parse(
            ctx.message.content, None, adjudicator.provinces, adjudicator
        )

    player = utils.get_player(ctx.author, adjudicator)
    if player is not None:
        if not utils.is_player_channel(player.name, ctx.channel):
            raise RuntimeError(
                "You cannot order as a player outside of your orders channel."
            )
        return diplomacy.order.parse(
            ctx.message.content, player, adjudicator.provinces, adjudicator
        )

    raise PermissionError(
        "You cannot order any units because you are neither a GM nor a player."
    )


def view_orders(ctx: commands.Context) -> str:
    if utils.is_gm(ctx.author):
        if not utils.is_gm_channel(ctx.channel):
            raise RuntimeError("You cannot view orders as a GM in a non-GM channel.")
        return adjudicator.mapper.get_moves_map(None)

    player = utils.get_player(ctx.author, adjudicator)
    if player is not None:
        if not utils.is_player_channel(player.name, ctx.channel):
            raise RuntimeError(
                "You cannot view orders as a player outside of your orders channel."
            )
        return adjudicator.mapper.get_moves_map(player)

    raise PermissionError(
        "You cannot view orders because you are neither a GM nor a player."
    )


def adjudicate(ctx: commands.Context) -> str:
    if not utils.is_gm(ctx.author):
        raise PermissionError("You cannot adjudicate because you are not a GM.")

    if not utils.is_gm_channel(ctx.channel):
        raise RuntimeError("You cannot adjudicate in a non-GM channel.")

    global adjudicator
    return adjudicator.adjudicate()


def rollback(ctx: commands.Context) -> str:
    if not utils.is_gm(ctx.author):
        raise PermissionError("You cannot rollback because you are not a GM.")

    if not utils.is_gm_channel(ctx.channel):
        raise RuntimeError("You cannot rollback in a non-GM channel.")

    global adjudicator
    return adjudicator.rollback()


def get_scoreboard(ctx: commands.Context) -> str:
    if not utils.is_gm(ctx.author):
        raise PermissionError("You cannot get the scoreboard because you are not a GM.")

    if not utils.is_gm_channel(ctx.channel):
        raise RuntimeError("You cannot get the scoreboard in a non-GM channel.")

    counts_list = []
    for player, count in adjudicator.get_build_counts().items():
        counts_list.append((player, count))
    counts_list = sorted(counts_list, key=lambda counts: counts[1])

    response = ""
    for player, count in counts_list:
        response += f"{player} {count}\n"

    return response


def edit(ctx: commands.Context) -> str:
    if not utils.is_gm(ctx.author):
        raise PermissionError(
            "You cannot edit the board state because you are not a GM."
        )

    if not utils.is_gm_channel(ctx.channel):
        raise RuntimeError("You cannot edit the board state in a non-GM channel.")

    # TODO: (DB) implement edit state
    raise RuntimeError(
        "Edit state has not been implemented yet and is not needed until the bot is running via server."
    )


def initialize_board_setup(ctx: commands.Context) -> str:
    if not utils.is_gm(ctx.author):
        raise PermissionError(
            "You cannot initialize the board state because you are not a GM."
        )
    if not utils.is_gm_channel(ctx.channel):
        raise RuntimeError("You cannot initialize the board state in a non-GM channel.")

    board = parse_board()
    global adjudicator
    adjudicator = Adjudicator(board)
    return "Setup completed successfully!"
