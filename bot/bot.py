import discord

from discord.ext import commands

from _token import DISCORD_TOKEN
from adjudicate import adjudicator
from board import board
from bot import orders, utils

intent = discord.Intents.default()
intent.message_content = True
bot = discord.Client(intents=intent, command_prefix='.', help_command=None)


@bot.event
async def on_ready():
    print('Bot is ready!')


@commands.command
async def ping(ctx):
    await ctx.channel.send('Beep Boop')


@commands.command
async def order(ctx):
    response = orders.parse(ctx.message)
    await ctx.channel.send(response)


@commands.command
async def view_orders(ctx):
    player = utils.get_player(ctx.message.author)
    response = board.get(player)
    await ctx.channel.send(response)


@commands.command
async def adjudicate(ctx):
    author = utils.get_player(ctx.message.author)
    response = adjudicator.adjudicate(author)
    await ctx.channel.send(response)


@commands.command
async def rollback(ctx):
    author = utils.get_player(ctx.message.author)
    response = adjudicator.rollback(author)
    await ctx.channel.send(response)


@commands.command
async def scoreboard(ctx):
    response = utils.get_scoreboard()
    await ctx.channel.send(response)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)

# TODO: test commands
# TODO: commands
#  .help
