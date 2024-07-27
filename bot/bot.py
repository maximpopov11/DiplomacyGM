from typing import NoReturn, Callable

import discord
from discord.ext import commands

import bot.command as command
from bot._token import DISCORD_TOKEN


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

commandFunctionType = Callable[[commands.Context], str]


@bot.event
async def on_ready():
    # TODO: (FRAMEWORK) setup db (make sure it's stable) / use files if it'll take too long to write (state, game id)
    # TODO: (IMPL) read ctx.guild.id (or equivalent) and store that in db API
    # TODO: (IMPL) get state from db and create adjudicator
    # TODO: (IMPL) update state -> update db (protect against malicious inputs like drop table)
    pass


async def handle_command(function: commandFunctionType, ctx: discord.ext.commands.Context) -> NoReturn:
    try:
        response = function(ctx)
        await ctx.channel.send(response)
    except Exception as e:
        await ctx.channel.send('Command errored: ' + str(e))


@bot.command(help='Checks bot listens and responds')
async def ping(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.ping, ctx)


@bot.command(brief='Submits orders (one per line)')
async def order(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.order, ctx)


@bot.command(brief='Outputs the map with your current submitted moves shown')
async def view_orders(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.view_orders, ctx)


@bot.command(brief='Adjudicates the game and outputs the moves and results maps')
async def adjudicate(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.adjudicate, ctx)


@bot.command(brief='Rolls back to the previous game state and outputs the results map')
async def rollback(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.rollback, ctx)


@bot.command(brief='Outputs the scoreboard')
async def scoreboard(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.get_scoreboard, ctx)


@bot.command(brief='Edits the game state and outputs the results map')
async def edit(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.edit, ctx)


@bot.command(brief='Parses the input map image file')
async def initialize_board_setup(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.initialize_board_setup, ctx)


def run():
    bot.run(DISCORD_TOKEN)
