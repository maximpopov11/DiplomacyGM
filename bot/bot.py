import discord
from discord.ext import commands

import utils

from _token import DISCORD_TOKEN
from adjudicate import adjudicator
from diplomacy.board import board
from diplomacy.order import parse as parse_order

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)


@bot.event
async def on_ready():
    print('Bot is ready!')


async def try_command(command, ctx):
    try:
        await command(ctx)
    except Exception as e:
        await ctx.channel.send('Command errored with description: ' + str(e))


@bot.command()
async def ping(ctx):
    await try_command(_ping, ctx)


async def _ping(ctx):
    await ctx.channel.send('Beep Boop')


@bot.command()
async def order(ctx):
    await try_command(_order, ctx)


async def _order(ctx):
    response = parse_order(ctx.message.content)
    await ctx.channel.send(response)


@bot.command()
async def view_orders(ctx):
    await try_command(_view_orders, ctx)


async def _view_orders(ctx):
    player = utils.get_player(ctx.message.author)
    response = board.get(player)
    await ctx.channel.send(response)


@bot.command()
async def adjudicate(ctx):
    await try_command(_adjudicate, ctx)


async def _adjudicate(ctx):
    author = utils.get_player(ctx.message.author)
    response = adjudicator.adjudicate(author)
    await ctx.channel.send(response)


@bot.command()
async def rollback(ctx):
    await try_command(_rollback, ctx)


async def _rollback(ctx):
    author = utils.get_player(ctx.message.author)
    response = adjudicator.rollback(author)
    await ctx.channel.send(response)


@bot.command()
async def scoreboard(ctx):
    await try_command(_scoreboard, ctx)


async def _scoreboard(ctx):
    response = utils.get_scoreboard()
    await ctx.channel.send(response)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
