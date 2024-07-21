import discord
from discord.ext import commands

import orders
import utils

from _token import DISCORD_TOKEN
from adjudicate import adjudicator
from board import board

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)


@bot.event
async def on_ready():
    print('Bot is ready!')


@bot.command()
async def ping(ctx):
    await ctx.channel.send('Beep Boop')


@bot.command()
async def order(ctx):
    response = orders.parse(ctx.message)
    await ctx.channel.send(response)


@bot.command()
async def view_orders(ctx):
    player = utils.get_player(ctx.message.author)
    response = board.get(player)
    await ctx.channel.send(response)


@bot.command()
async def adjudicate(ctx):
    author = utils.get_player(ctx.message.author)
    response = adjudicator.adjudicate(author)
    await ctx.channel.send(response)


@bot.command()
async def rollback(ctx):
    author = utils.get_player(ctx.message.author)
    response = adjudicator.rollback(author)
    await ctx.channel.send(response)


@bot.command()
async def scoreboard(ctx):
    response = utils.get_scoreboard()
    await ctx.channel.send(response)


# TODO: this should live in a class
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
