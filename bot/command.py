import random

from discord.ext import commands

import diplomacy.order
import diplomacy.persistence.state
from diplomacy.adjudicate import adjudicator

none = 'none'

players = {
    none,
    'player 1',
}


# TODO: improve get role; should be checked in here, not passed along
def get_player(author) -> str:
    for role in author.roles:
        if role in players:
            return role
    return none


ping_text_choices = {
    'proudly states',
    'fervently believes in the power of'
    'is being mind controlled by'
}


def ping(ctx: commands.Context) -> str:
    response = 'Beep Boop'
    if random.random() < 0.1:
        author = ctx.message.author
        content = ctx.message.content
        response = author + ' ' + random.choice(ping_text_choices) + ' ' + content
    return response


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


def get_scoreboard(_: commands.Context) -> str:
    return 'pretend this is the scoreboard'


def edit(_: commands.Context) -> str:
    return 'looks like the GM would like to manually fix something, too bad this is not implemented yet'


def initialize_board_setup(ctx: commands.Context) -> str:
    return 'pretend the board setup is done'
