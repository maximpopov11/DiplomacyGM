import os
from typing import Callable

import discord
from discord.ext import commands

from bot import command
from diplomacy.persistence.manager import Manager

# TODO: (BETA) this should live in a class
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

manager = Manager()


# TODO: (BETA) improve help to display player/GM/admin/shared commands and with extra descriptions for command help
async def _handle_command(
    function: Callable[[commands.Context, Manager], str], ctx: discord.ext.commands.Context
) -> None:
    try:
        response = function(ctx, manager)
        await ctx.channel.send(response)
    except Exception as e:
        await ctx.channel.send("Command errored: " + str(e))


@bot.command(help="Checks bot listens and responds")
async def ping(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.ping, ctx)


# TODO: (BETA) allow ambiguous moves/convoys
# TODO: (BETA) warn move incompatible for supports when supported move not ordered
@bot.command(
    brief="Submits orders (one per line). Note: convoy moves must explicitly include 'via convoy' at this time."
)
async def order(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.order, ctx)


@bot.command(brief="Outputs the map with your current submitted moves shown")
async def view_orders(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.view_orders, ctx)


@bot.command(brief="Adjudicates the game and outputs the moves and results maps")
async def adjudicate(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.adjudicate, ctx)


@bot.command(brief="Rolls back to the previous game state and outputs the results map")
async def rollback(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.rollback, ctx)


@bot.command(brief="Outputs the scoreboard")
async def scoreboard(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.get_scoreboard, ctx)


@bot.command(
    brief="Edits the game state and outputs the results map. "
    "Note: you cannot edit inherent map state (eg. province adjacency)."
)
async def edit(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.edit, ctx)


@bot.command(brief="Create a game of Imp Dip and output the map. (there are no other variant options at this time)")
async def create_game(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.create_game, ctx)


def run():
    token = os.getenv("DISCORD_TOKEN")
    bot.run(token)
