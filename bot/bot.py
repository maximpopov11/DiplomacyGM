from typing import Callable, NoReturn

import discord
from discord.ext import commands

import command
from _token import DISCORD_TOKEN

# TODO: this and the main stuff should live in a class
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

# TODO: ensure all private commands (both player and GM) are illegal in non order/GM channels
# TODO: all commands should have an output/confirmation
# TODO: help command should describe commands
# TODO: implement & test all bot API commands


commandFunctionType = Callable[[discord.ext.commands.Context], str]


async def handle_command(function: commandFunctionType, ctx: discord.ext.commands.Context) -> NoReturn:
    try:
        response = function(ctx)
        await ctx.channel.send(response)
    except Exception as e:
        await ctx.channel.send('Command errored with description: ' + str(e))


@bot.command()
async def ping(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.ping, ctx)


@bot.command()
async def order(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.order, ctx)


@bot.command()
async def view_orders(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.view_orders, ctx)


@bot.command()
async def adjudicate(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.adjudicate, ctx)


@bot.command()
async def rollback(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.rollback, ctx)


@bot.command()
async def scoreboard(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.get_scoreboard, ctx)


@bot.command()
async def edit(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.edit, ctx)


@bot.command()
async def initialize_board_setup(ctx: discord.ext.commands.Context) -> NoReturn:
    await handle_command(command.initialize_board_setup, ctx)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
