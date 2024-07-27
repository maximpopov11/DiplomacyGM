from discord.ext import commands

import diplomacy.order
import diplomacy.persistence.state
from diplomacy.adjudicate import adjudicator

none = 'none'

players = {
    none,
    'player 1',
}


# TODO: improve get role
def get_player(author) -> str:
    for role in author.roles:
        if role in players:
            return role
    return none


def ping(ctx: commands.Context) -> str:
    return 'Beep Boop'


def order(ctx: commands.Context) -> str:
    return diplomacy.order.parse(ctx.message.content)


def view_orders(ctx: commands.Context) -> str:
    player = get_player(ctx.message.author)
    return diplomacy.persistence.state.get(player)


def adjudicate(ctx: commands.Context) -> str:
    author = get_player(ctx.message.author)
    return adjudicator.adjudicate(author)


def rollback(ctx: commands.Context) -> str:
    author = get_player(ctx.message.author)
    return adjudicator.rollback(author)


def get_scoreboard(ctx: commands.Context) -> str:
    return 'pretend this is the scoreboard'


def initialize_board_setup(ctx: commands.Context) -> str:
    return 'pretend the board setup is done'
