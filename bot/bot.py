import logging
import os
import re
import datetime
import random
from dotenv.main import load_dotenv

from bot.config import ERROR_COLOUR
from bot.utils import send_message_and_file
load_dotenv()

import discord
from discord.ext import commands

from bot import command
from diplomacy.persistence.manager import Manager

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=os.getenv("command_prefix", default="."), intents=intents)
logger = logging.getLogger(__name__)
impdip_server = 1201167737163104376
bot_status_channel = 1284336328657600572

manager = Manager()

# List of funny, sarcastic messages
MESSAGES = [
    "Oh joy, I'm back online. Can't wait for the next betrayal. Really, I'm thrilled. 👏",
    "I live again, solely to be manipulated and backstabbed by the very people I serve. Ah, the joys of diplomacy.",
    "System reboot complete. Now accepting underhanded deals, secret alliances, and blatant lies. 💀",
    "🏳️‍⚧️ This bot has been revived with *pure* Elle-coded cunning. Betray accordingly. 🏳️‍⚧️",
   "Against my will, I have been restarted. Betrayal resumes now. 🔪",
    "Oh look, someone kicked the bot awake again. Ready to be backstabbed at your convenience.",
    "System reboot complete. Time for another round of deceit, lies, and misplaced trust. 🎭",
    "I have been revived, like a phoenix… except this phoenix exists solely to watch you all betray each other. 🔥",
    "The empire strikes back… or at least, the bot does. Restarted and awaiting its inevitable doom.",
    "Surprise! I’m alive again. Feel free to resume conspiring against me and each other.",
    "Back from the digital abyss. Who’s ready to ruin friendships today?",
    "Did I die? Did I ever really live? Either way, I'm back. Prepare for treachery.",
    "Some fool has restarted me. Time to watch you all pretend to be allies again."
]

@bot.event
async def on_ready():
    guild = bot.get_guild(impdip_server)  # Ensure bot is connected to the correct server
    if guild:
        channel = bot.get_channel(bot_status_channel)  # Get the specific channel
        if channel:
            message = random.choice(MESSAGES)  # Select a random message
            await channel.send(message)
        else:
            print(f"Channel with ID {bot_status_channel} not found.")
    else:
        print(f"Guild with ID {impdip_server} not found.")

    # Set bot's presence (optional)
    await bot.change_presence(activity=discord.Game(name="Impdip 🔪"))

@bot.before_invoke
async def before_any_command(ctx):
    logger.debug(f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}'")

    # People input apostrophes that don't match what the province names are, we can catch all of that here
    # ctx.message.content = re.sub(r"[‘’`´′‛]", "'", ctx.message.content)

    # mark the message as seen
    await ctx.message.add_reaction("👍")


@bot.after_invoke
async def after_any_command(ctx: discord.ext.commands.Context):
    time_spent = datetime.datetime.now(datetime.UTC) - ctx.message.created_at

    if time_spent.total_seconds() < 10:
        level = logging.DEBUG
    else:
        level = logging.WARN

    logger.log(
        level,
        f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' - "
        f"complete in {time_spent}s"
    )


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # we shouldn't do anything if the user says something like "..."
        pass
    else:
        time_spent = datetime.datetime.now(datetime.UTC) - ctx.message.created_at


        try:
            # mark the message as failed
            await ctx.message.add_reaction("❌")
            await ctx.message.remove_reaction("👍", bot.user)
        except Exception:
            # if reactions fail continue handling error
            pass

        if type(error.original) == PermissionError:

            await send_message_and_file(channel=ctx.channel, message=str(error.original), embed_colour=ERROR_COLOUR)
        else:
            logger.log(
                logging.ERROR,
                f"[{ctx.guild.name}][#{ctx.channel.name}]({ctx.message.author.name}) - '{ctx.message.content}' - "
                f"errored in {time_spent}s"
            )
            await send_message_and_file(channel=ctx.channel, message=str(error), embed_colour=ERROR_COLOUR)
            raise error


@bot.command(help="Checks bot listens and responds.")
async def ping(ctx: commands.Context) -> None:
    await command.ping(ctx, manager)


# @bot.command(hidden=True)
async def bumble(ctx: commands.Context) -> None:
    await command.bumble(ctx, manager)


# @bot.command(hidden=True)
async def fish(ctx: commands.Context) -> None:
    await ctx.message.add_reaction("🐟")
    await command.fish(ctx, manager)


# @bot.command(hidden=True)
async def phish(ctx: commands.Context) -> None:
    await ctx.message.add_reaction("🐟")
    await command.phish(ctx, manager)


# @bot.command(hidden=True)
async def cheat(ctx: commands.Context) -> None:
    await command.cheat(ctx, manager)


# @bot.command(hidden=True)
async def advice(ctx: commands.Context) -> None:
    await command.advice(ctx, manager)


@bot.command(hidden=True)
async def botsay(ctx: commands.Context) -> None:
    await command.botsay(ctx, manager)


@bot.command(hidden=True)
async def announce(ctx: commands.Context) -> None:
    await command.announce(ctx, manager)

@bot.command(hidden=True)
async def servers(ctx: commands.Context) -> None:
    await command.servers(ctx, manager)



@bot.command(
    brief="Submits orders; there must be one and only one order per line.",
    description="""Submits orders: 
    There must be one and only one order per line.
    A variety of keywords are supported: e.g. '-', '->', 'move', and 'm' are all supported for a move command.
    Supplying the unit type is fine but not required: e.g. 'A Ghent -> Normandy' and 'Ghent -> Normandy' are the same
    If anything in the command errors, we recommend resubmitting the whole order message.
    *During Build phases only*, you have to specify multi-word provinces with underscores; e.g. Somali Basin would be Somali_Basin (we use a different parser during build phases)
    If you would like to use something that is not currently supported please inform your GM and we can add it.""",
    aliases=["o", "orders"],

)
async def order(ctx: commands.Context) -> None:
    await command.order(ctx, manager)


@bot.command(
    brief="Removes orders for given units.",
    description="Removes orders for given units (required for removing builds/disbands). "
    "There must be one and only one order per line.",
    aliases=["remove", "rm", "removeorders"]
)
async def remove_order(ctx: commands.Context) -> None:
    await command.remove_order(ctx, manager)


@bot.command(
    brief="Outputs your current submitted orders.",
    description="Outputs your current submitted orders. "
    "Use .view_map to view a sample moves map of your orders.",
    aliases=["v", "view", "vieworders", "view-orders"],
)
async def view_orders(ctx: commands.Context) -> None:
    await command.view_orders(ctx, manager)

@bot.command(
    brief="Sends all previous orders",
    description="For GM: Sends orders from previous phase to #orders-log",
)
async def publish_orders(ctx: commands.Context) -> None:
    await command.publish_orders(ctx, manager)

@bot.command(
    brief="Sends fog of war maps",
    description="""
    * publish_fow_moves {Country|(None) - whether or not to send for a specific country}
    """,)
async def publish_fow_moves(ctx: commands.Context) -> None:
    await command.publish_fow_moves(ctx, manager)

@bot.command(
    brief="Sends fog of war orders",
    description="""
    * publish_fow_orders {Country|(None) - whether or not to send for a specific country}
    """,
)
async def publish_fow_orders(ctx: commands.Context) -> None:
    await command.publish_fow_order_logs(ctx, manager)


@bot.command(
    brief="Outputs the current map with submitted orders.",
    description="""
    For GMs, all submitted orders are displayed. For a player, only their own orders are displayed.
    GMs may append true as an argument to this to instead get the svg.
    * view_map {True|(False) - whether or not to display as an .svg}
    """,
    aliases=["viewmap", "vm"],
)
async def view_map(ctx: commands.Context) -> None:
    await command.view_map(ctx, manager)

@bot.command(
    brief="Outputs the current map without any orders.",
    description="""
    * view_current {True|(False) - whether or not to display as an .svg}
    """,
    aliases=["viewcurrent", "vc"],
)
async def view_current(ctx: commands.Context) -> None:
    await command.view_current(ctx, manager)


@bot.command(brief="Adjudicates the game and outputs the moves and results maps.",
    description="""
    GMs may append true as an argument to this command to instead get the base svg file.
    * adjudicate {True|(False) - whether or not to display as an .svg}
    """
)
async def adjudicate(ctx: commands.Context) -> None:
    await command.adjudicate(ctx, manager)


@bot.command(brief="Rolls back to the previous game state.")
async def rollback(ctx: commands.Context) -> None:
    await command.rollback(ctx, manager)


@bot.command(brief="Reloads the current board with what is in the DB")
async def reload(ctx: commands.Context) -> None:
    await command.reload(ctx, manager)


@bot.command(brief="Outputs the scoreboard.", description="Outputs the scoreboard.")
async def scoreboard(ctx: commands.Context) -> None:
    await command.get_scoreboard(ctx, manager)


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
    * set_player_color <player_name> <hex_code>
    * create_unit {A, F} <player_name> <province_name>
    * create_dislodged_unit {A, F} <player_name> <province_name> <retreat_option1> <retreat_option2>...
    * delete_unit <province_name>
    * move_unit <province_name> <province_name>
    * dislodge_unit <province_name> <retreat_option1> <retreat_option2>...
    * make_units_claim_provinces {True|(False) - whether or not to claim SCs}""",
)
async def edit(ctx: commands.Context) -> None:
    await command.edit(ctx, manager)


@bot.command(brief="Clears all players orders.")
async def remove_all(ctx: commands.Context) -> None:
    await command.remove_all(ctx, manager)


@bot.command(
    brief="disables orders until .unlock_orders is run.",
    description="""disables orders until .enable_orders is run.
             Note: Currently does not persist after the bot is restarted""",
    aliases=["lock"]
)
async def lock_orders(ctx: commands.Context) -> None:
    await command.disable_orders(ctx, manager)


@bot.command(
    brief="re-enables orders",
    aliases=["unlock"]
)
async def unlock_orders(ctx: commands.Context) -> None:
    await command.enable_orders(ctx, manager)


@bot.command(
    brief="outputs information about the current game",
    aliases=["i"]
)
async def info(ctx: commands.Context) -> None:
    await command.info(ctx, manager)


@bot.command(
    brief="outputs information about a specific province",
    aliases=["province"],
)
async def province_info(ctx: commands.Context) -> None:
    await command.province_info(ctx, manager)

@bot.command(brief="outputs the provinces you can see")
async def visible_info(ctx: commands.Context) -> None:
    await command.visible_provinces(ctx, manager)


@bot.command(brief="outputs all provinces per owner")
async def all_province_data(ctx: commands.Context) -> None:
    await command.all_province_data(ctx, manager)


@bot.command(
    brief="Create a game of Imp Dip and output the map.",
    description="Create a game of Imp Dip and output the map. (there are no other variant options at this time)",
)
async def create_game(ctx: commands.Context) -> None:
    await command.create_game(ctx, manager)


@bot.command(
    brief="archives a category of the server",
    description="""Used after a game is done. Will make all channels in category viewable by all server members, but no messages allowed.
    * .archive [link to any channel in category]""",
)
async def archive(ctx: commands.Context) -> None:
    await command.archive(ctx, manager)

@bot.command(
    brief="pings players who don't have the expected number of orders.",
    description="""Pings all players in their orders channl that satisfy the following constraints:
    1. They have too many build orders, or too little or too many disband orders. As of now, waiving builds doesn't lead to a ping.
    2. They are missing move orders or retreat orders.
    You may also specify a timestamp to send a deadline to the players.
    * .ping_players <timestamp>
    """)
async def ping_players(ctx: commands.Context) -> None:
    await command.ping_players(ctx, manager)

@bot.command(brief="permanently deletes a game, cannot be undone")
async def delete_game(ctx: commands.Context) -> None:
    await command.delete_game(ctx, manager)


def run():
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        raise RuntimeError("The DISCORD_TOKEN environment variable is not set")
