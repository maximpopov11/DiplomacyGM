import logging
import os
from typing import Callable

import discord
from discord.ext import commands

# from assets.secrets import __DISCORD_TOKEN
from bot import command
from diplomacy.persistence.manager import Manager

# TODO: (BETA) this should live in a class
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)
logger = logging.getLogger(__name__)

manager = Manager()


async def _handle_command(
    function: Callable[[commands.Context, Manager], tuple[str, str | None]],
    ctx: discord.ext.commands.Context,
) -> None:
    try:
        # TODO: (!) stack trace on logging failed commands
        logger.debug(f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}'")
        response, file_name = function(ctx, manager)
        logger.debug(
            f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' -> \n{response}"
        )
        while 2000 < len(response):
            # Try to find an even line break to split the message on
            cutoff = response.rfind("\n", 0, 2000)
            if cutoff == -1:
                cutoff = 2000
            await ctx.channel.send(response[:cutoff].strip())
            response = response[cutoff:].strip()
        if file_name is not None:
            await ctx.channel.send(response, file=discord.File(file_name))
        else:
            await ctx.channel.send(response)
    except Exception as e:
        logger.error(
            f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) "
            f"invoking '{getattr(function, '__name__', 'Unknown')}': {repr(e)}"
        )
        logger.error("", exc_info=e)
        await ctx.channel.send("Command errored: ```" + str(e) + "```")


@bot.command(help="Checks bot listens and responds.")
async def ping(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.ping, ctx)


@bot.command(hidden=True)
async def bumble(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.bumble, ctx)


# TODO: (BETA) allow ambiguous moves/convoys
# TODO: (BETA) warn move incompatible for supports when supported move not ordered
# TODO: (BETA) allow personal command dictionary editing
@bot.command(
    brief="Submits orders; there must be one and only one order per line.",
    description="""Submits orders: 
    There must be one and only one order per line.
    All multi-word concepts must be separated by a '_'.
        e.g. 'New York North Coast' should be 'New_York_North_Coast'.
    Convoy moves must be explicitly specified at this time due to adjudication library constraints, meaning 'A move B' and 'A convoy_move B' are not the same.
    A variety of keywords are supported: e.g. '-', 'move', and 'm' are all supported for a move command.
    If you would like to use something that is not currently supported please inform your GM and we can add it.""",
)
async def order(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.order, ctx)


@bot.command(
    brief="Removes orders for given units.",
    description="Removes orders for given units (required for removing builds/disbands). "
    "There must be one and only one order per line.",
)
async def remove_order(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.remove_order, ctx)


@bot.command(
    brief="Outputs your current submitted orders.",
    description="Outputs your current submitted orders. "
    "In the future we will support outputting a sample moves map of your orders.",
)
async def view_orders(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.view_orders, ctx)


@bot.command(brief="Adjudicates the game and outputs the moves and results maps.")
async def adjudicate(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.adjudicate, ctx)


@bot.command(brief="Rolls back to the previous game state and outputs the results map.")
async def rollback(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.rollback, ctx)


@bot.command(brief="Outputs the scoreboard.", description="Outputs the scoreboard.")
async def scoreboard(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.get_scoreboard, ctx)


@bot.command(
    brief="Edits the game state and outputs the results map.",
    description="""Edits the game state and outputs the results map. 
    There must be one and only one command per line.
    Note: you cannot edit immalleable map state (eg. province adjacency).
    The following are the supported sub-commands:
    * set_phase {spring, fall, winter}_{moves, retreats, builds}
    * set_core <province_name> <player_name>
    * set_half_core <province_name> <player_name>
    * set_province_owner <province_name> <player_name>
    * create_unit {A, F} <player_name> <province_name>
    * delete_unit <province_name>
    * move_unit <province_name> <province_name>
    * make_units_claim_provinces {True|(False) - whether or not to claim SCs}""",
)
async def edit(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.edit, ctx)


@bot.command(brief="Clears all players orders.")
async def remove_all(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.remove_all, ctx)


@bot.command(
    brief="disables orders until .enable_orders is run.",
    discription="""disables orders until .enable_orders is run.
             Note: Currently does not persist after the bot is restarted""",
)
async def disable_orders(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.disable_orders, ctx)


@bot.command(brief="reenables orders")
async def enable_orders(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.enable_orders, ctx)


@bot.command(brief="outputs information about the current game")
async def info(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(commands.info, ctx)


# TODO: (DB) output the map
@bot.command(
    brief="Create a game of Imp Dip and output the map.",
    description="Create a game of Imp Dip and output the map. (there are no other variant options at this time)",
)
async def create_game(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.create_game, ctx)


def run():
    token = os.getenv("DISCORD_TOKEN")
    # token = __DISCORD_TOKEN
    if token:
        bot.run(token)
    else:
        print("The DISCORD_TOKEN enviroment variable is not set")
