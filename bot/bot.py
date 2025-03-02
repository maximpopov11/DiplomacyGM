import logging
import os
import re
import time
from typing import Callable
import inspect
import zipfile
import io

import discord
from discord import HTTPException
from discord.ext import commands

from bot import command
from diplomacy.persistence.manager import Manager

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)
logger = logging.getLogger(__name__)
discord_message_limit = 2000
discord_file_limit = 10 * (2**20)

manager = Manager()


@bot.before_invoke
async def before_any_command(ctx):
    logger.debug(f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}'")

    # mark the message as seen
    await ctx.message.add_reaction("👍")


@bot.after_invoke
async def after_any_command(ctx):
    logger.debug(
        f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' - complete"
    )
    pass


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # we shouldn't do anything if the user says something like "..."
        pass
    else:
        logger.error(
            f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}': {repr(error)}",
            exc_info=error,
        )

        # mark the message as failed
        await ctx.message.add_reaction("❌")
        await ctx.message.remove_reaction("👍", bot.user)

        await ctx.send(error)


async def _handle_command(
    function: Callable[[commands.Context, Manager], tuple[str, str | None]],
    ctx: discord.ext.commands.Context,
) -> None:
    start = time.time()

    # People input apostrophes that don't match what the province names are, we can catch all of that here
    ctx.message.content = re.sub(r"[‘’`´′‛]", "'", ctx.message.content)

    if inspect.iscoroutinefunction(function):
        response = await function(ctx, manager)
    else:
        response = function(ctx, manager)

    if type(response) is dict:
        message, file, file_name = response["message"], response["file"], response["file_name"]
    else:
        message, file = response, None

    while discord_message_limit < len(message):
        # Try to find an even line break to split the message on
        cutoff = message.rfind("\n", 0, discord_message_limit)
        if cutoff == -1:
            cutoff = discord_message_limit
        await ctx.channel.send(message[:cutoff].strip())
        message = message[cutoff:].strip()
    if file is not None and len(file) > discord_file_limit:
        # zip compression without using files (disk is slow)

        # We create a virtual file, write to it, and then restart it
        # for some reason zipfile doesn't support this natively
        with io.BytesIO() as vfile:
            zip_file = zipfile.ZipFile(vfile, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=9)
            zip_file.writestr(f"{file_name}.svg", file, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            zip_file.close()
            vfile.seek(0)
            await ctx.channel.send(message, file=discord.File(fp=vfile, filename=f"{file_name}.zip"))
    elif file is not None:
        with io.BytesIO(file) as vfile:
            await ctx.channel.send(message, file=discord.File(fp=vfile, filename=f"{file_name}.svg"))
    else:
        await ctx.channel.send(message)

    elapsed = time.time() - start
    logger.debug(
        f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' -> \n{message} | {elapsed}s"
    )


@bot.command(help="Checks bot listens and responds.")
async def ping(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.ping, ctx)


# @bot.command(hidden=True)
async def bumble(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.bumble, ctx)


# @bot.command(hidden=True)
async def fish(ctx: discord.ext.commands.Context) -> None:
    await ctx.message.add_reaction("🐟")
    await _handle_command(command.fish, ctx)


# @bot.command(hidden=True)
async def phish(ctx: discord.ext.commands.Context) -> None:
    await ctx.message.add_reaction("🐟")
    await _handle_command(command.phish, ctx)


# @bot.command(hidden=True)
async def cheat(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.cheat, ctx)


# @bot.command(hidden=True)
async def advice(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.advice, ctx)


@bot.command(hidden=True)
async def botsay(ctx: discord.ext.commands.Context) -> None:
    await command.botsay(ctx, manager)


@bot.command(hidden=True)
async def announce(ctx: discord.ext.commands.Context) -> None:
    await command.announce(ctx, {bot.get_guild(server_id) for server_id in manager.list_servers()})


@bot.command(
    brief="Submits orders; there must be one and only one order per line.",
    description="""Submits orders: 
    There must be one and only one order per line.
    A variety of keywords are supported: e.g. '-', '->', 'move', and 'm' are all supported for a move command.
    Supplying the unit type is fine but not required: e.g. 'A Ghent -> Normandy' and 'Ghent -> Normandy' are the same
    If anything in the command errors, we recommend resubmitting the whole order message.
    *During Build phases only*, you have to specify multi-word provinces with underscores; e.g. Somali Basin would be Somali_Basin (we use a different parser during build phases)
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


@bot.command(brief="Outputs the current map with submitted orders.")
async def view_map(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.view_map, ctx)


@bot.command(brief="Adjudicates the game and outputs the moves and results maps.")
async def adjudicate(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.adjudicate, ctx)


@bot.command(brief="Rolls back to the previous game state.")
async def rollback(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.rollback, ctx)


@bot.command(brief="Reloads the current board with what is in the DB")
async def reload(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.reload, ctx)


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
    * create_dislodged_unit {A, F} <player_name> <province_name> <retreat_option1> <retreat_option2>...
    * delete_unit <province_name>
    * move_unit <province_name> <province_name>
    * dislodge_unit <province_name> <retreat_option1> <retreat_option2>...
    * make_units_claim_provinces {True|(False) - whether or not to claim SCs}""",
)
async def edit(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.edit, ctx)


@bot.command(brief="Clears all players orders.")
async def remove_all(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.remove_all, ctx)


@bot.command(
    brief="disables orders until .unlock_orders is run.",
    description="""disables orders until .enable_orders is run.
             Note: Currently does not persist after the bot is restarted""",
)
async def lock_orders(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.disable_orders, ctx)


@bot.command(brief="re-enables orders")
async def unlock_orders(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.enable_orders, ctx)


@bot.command(brief="outputs information about the current game")
async def info(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.info, ctx)


@bot.command(brief="outputs information about a specific province")
async def province_info(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.province_info, ctx)


@bot.command(brief="outputs all provinces per owner")
async def all_province_data(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.all_province_data, ctx)


@bot.command(
    brief="Create a game of Imp Dip and output the map.",
    description="Create a game of Imp Dip and output the map. (there are no other variant options at this time)",
)
async def create_game(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.create_game, ctx)


@bot.command(
    brief="archives a category of the server",
    description="Used after a game is done. Will make all channels in category viewable by all server members, but no messages allowed.)",
)
async def archive(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.archive, ctx)


@bot.command(brief="permanently deletes a game, cannot be undone")
async def delete_game(ctx: discord.ext.commands.Context) -> None:
    await _handle_command(command.delete_game, ctx)


def run():
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        raise RuntimeError("The DISCORD_TOKEN environment variable is not set")
