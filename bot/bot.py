from typing import NoReturn, Callable

import discord
from discord.ext import commands

import command
from _token import DISCORD_TOKEN


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

commandFunctionType = Callable[[commands.Context], str]


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


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
