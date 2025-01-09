import itertools
import logging
import random
from random import randrange

from discord import Guild
from discord.ext import commands

import bot.perms as perms
from bot.config import is_bumble, temporary_bumbles
from bot.parse_edit_state import parse_edit_state
from bot.parse_order import parse_order, parse_remove_order
from bot.utils import is_gm_channel, get_orders, is_admin
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.player import Player

logger = logging.getLogger(__name__)

ping_text_choices = [
    "proudly states",
    "fervently believes in the power of",
    "is being mind controlled by",
]


def ping(ctx: commands.Context, _: Manager) -> tuple[str, str | None]:
    response = "Beep Boop"
    if random.random() < 0.1:
        author = ctx.message.author
        content = ctx.message.content.removeprefix(".ping")
        if content == "":
            content = " nothing"
        name = author.nick
        if not name:
            name = author.name
        response = name + " " + random.choice(ping_text_choices) + content
    return response, None


def bumble(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    word_of_bumble = random.choice(["".join(perm) for perm in itertools.permutations("bumble")])

    if is_bumble(ctx.author.name) and random.randrange(0, 10) == 0:
        word_of_bumble = "bumble"

    if word_of_bumble == "bumble":
        word_of_bumble = "You are the chosen bumble"

        if ctx.author.name not in temporary_bumbles:
            # no keeping temporary bumbleship easily
            temporary_bumbles.add(ctx.author.name)
    if word_of_bumble == "elbmub":
        word_of_bumble = "elbmub nesohc eht era uoY"

    board = manager.get_board(ctx.guild.id)
    board.fish -= 1
    return f"**{word_of_bumble}**", None


def fish(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    fish_num = random.randrange(0, 20)

    debumblify = False
    if is_bumble(ctx.author.name) and random.randrange(0, 10) == 0:
        # Bumbles are good fishers
        if fish_num == 1:
            fish_num = 0
        elif fish_num > 15:
            fish_num -= 5

    if 0 == fish_num:
        # something special
        rare_fish_options = [
            ":dolphin:",
            ":shark:",
            ":duck:",
            ":goose:",
            ":dodo:",
            ":flamingo:",
            ":penguin:",
            ":unicorn:",
            ":swan:",
            ":whale:",
            ":seal:",
            ":sheep:",
            ":sloth:",
            ":hippopotamus:",
        ]
        board.fish += 10
        fish_message = f"**Caught a rare fish!** {random.choice(rare_fish_options)}"
    elif fish_num < 16:
        fish_num = (fish_num + 1) // 2
        board.fish += fish_num
        fish_emoji_options = [":fish:", ":tropical_fish:", ":blowfish:", ":jellyfish:", ":shrimp:"]
        fish_weights = [8, 4, 2, 1, 2]
        fish_message = f"Caught {fish_num} fish! " + " ".join(
            random.choices(fish_emoji_options, weights=fish_weights, k=fish_num)
        )
    else:
        fish_num = (21 - fish_num) // 2

        if is_bumble(ctx.author.name):
            if randrange(0, 20) == 0:
                # Sometimes Bumbles are so bad at fishing they debumblify
                debumblify = True
                fish_num = randrange(10, 20)
                return "", None
            else:
                # Bumbles that lose fish lose a lot of them
                fish_num *= randrange(3, 10)

        board.fish -= fish_num
        fish_kind = "captured" if board.fish >= 0 else "future"
        fish_message = f"Accidentally let {fish_num} {fish_kind} fish sneak away :("
    fish_message += f"\nIn total, {board.fish} fish have been caught!"
    if random.randrange(0, 5) == 0:
        get_connection().execute_arbitrary_sql(
            """UPDATE boards SET fish=? WHERE board_id=? AND phase=?""",
            (board.fish, board.board_id, board.get_phase_and_year_string()),
        )

    if debumblify:
        temporary_bumbles.remove(ctx.author.name)
        fish_message = f"\n Your luck has run out! {fish_message}\nBumble is sad, you must once again prove your worth by Bumbling!"

    return fish_message, None


def phish(ctx: commands.Context, _: Manager) -> tuple[str, str | None]:
    message = "No! Phishing is bad!"
    if is_bumble(ctx.author.name):
        message = "Please provide your firstborn pet and your soul for a chance at winning your next game!"
    return message, None


def cheat(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    message = "Cheating is disabled for this user."
    author = ctx.message.author.name
    board = manager.get_board(ctx.guild.id)
    if is_bumble(author):
        sample = random.choice(
            [
                f"It looks like {author} is getting coalitioned this turn :cry:",
                f"{author} is talking about stabbing {random.choice(list(board.players)).name} again",
                f"looks like he's throwing to {author}... shame",
                "yeah",
                "People in this game are not voiding enough",
                f"I can't believe {author} is moving to {random.choice(list(board.provinces)).name}",
                f"{author} has a bunch of invalid orders",
                f"No one noticed that {author} overbuilt?",
                f"{random.choice(list(board.players)).name} is in a perfect position to stab {author}"
            ]
        )
        message = f'Here\'s a helpful message I stole from the spectator chat: \n"{sample}"'
    return message, None


def advice(ctx: commands.Context, _: Manager) -> tuple[str, str | None]:
    message = "You are not worthy of advice."
    if is_bumble(ctx.author.name):
        message = "Bumble suggests that you go fishing, although typically blasphemous, today is your lucky day!"
    elif randrange(0, 5) == 0:
        message = random.choice(
            [
                "Bumble was surprised you asked him for advice and wasn't ready to give you any, maybe if you were a true follower...",
                "Icecream demands that you void more and will not be giving any advice until sated.",
                "Salt suggests that stabbing all of your neighbors is a good play in this particular situation.",
                "Ezio points you to an ancient proverb: see dot take dot.",
                "CaptainMeme advises balance of power play at this instance.",
                "Ash Lael deems you a sufficiently apt liar, go use those skills!",
                "Kwiksand suggests winning.",
                "The GMs suggest you input your orders so they don't need to hound you for them at the deadline.",
            ]
        )
    return message, None


@perms.gm("botsay")
async def botsay(ctx: commands.Context, _: Manager) -> None:
    # noinspection PyTypeChecker
    if len(ctx.message.channel_mentions) == 0:
        return
    channel = ctx.message.channel_mentions[0]
    content = ctx.message.content
    content = content.replace(".botsay", "").replace(channel.mention, "").strip()
    if len(content) == 0:
        return
    await ctx.message.add_reaction("👍")
    logger.info(f"{ctx.message.author.name} asked me to say '{content}' in {channel.name}")
    await channel.send(content)


async def announce(ctx: commands.Context, servers: set[Guild | None]) -> None:
    if not is_admin(ctx.message.author) and is_gm_channel(ctx.channel):
        return
    await ctx.message.add_reaction("👍")
    content = ctx.message.content.removeprefix(".announce").strip()
    logger.info(f"{ctx.message.author.name} sent announcement '{content}'")
    for server in servers:
        if server is None:
            continue
        admin_chat_channel = next(channel for channel in server.channels if is_gm_channel(channel))
        if admin_chat_channel is None:
            continue
        await admin_chat_channel.send(f"__Announcement__\n{ctx.message.author.display_name} says:\n{content}")


@perms.player("order")
def order(player: Player | None, ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)

    if player and not board.orders_enabled:
        return "Orders locked! If you think this is an error, contact a GM.", None

    return parse_order(ctx.message.content, player, board), None


@perms.player("remove orders")
def remove_order(player: Player | None, ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)

    if player and not board.orders_enabled:
        return "Orders locked! If you think this is an error, contact a GM.", None

    return parse_remove_order(ctx.message.content, player, board), None


@perms.player("view orders")
def view_orders(player: Player | None, ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    try:
        order_text = get_orders(manager.get_board(ctx.guild.id), player)
    except RuntimeError as err:
        logger.error(f"View_orders text failed in game with id: {ctx.guild.id}", exc_info=err)
        order_text = "view_orders text failed"
    if player is None:
        try:
            file_name = manager.draw_moves_map(ctx.guild.id, None)
        except Exception as err:
            logger.error(f"View_orders map failed in game with id: {ctx.guild.id}", exc_info=err)
            file_name = None
        return order_text, file_name

    else:
        # file_name = manager.draw_moves_map(ctx.guild.id, player)
        return order_text, None


@perms.gm("adjudicate")
def adjudicate(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    svg_file_name = manager.adjudicate(ctx.guild.id)
    return "Adjudication completed successfully.", svg_file_name


@perms.gm("rollback")
def rollback(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    return manager.rollback(ctx.guild.id)


@perms.gm("reload")
def reload(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    return manager.reload(ctx.guild.id)


@perms.gm("remove all orders")
def remove_all(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    for unit in board.units:
        unit.order = None

    database = get_connection()
    database.save_order_for_units(board, board.units)
    return "Successful", None


# @perms.gm("get scoreboard")
def get_scoreboard(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    response = ""
    for player in board.get_players_by_score():
        response += f"\n__{player.name}__: {len(player.centers)} ({'+' if len(player.centers) - len(player.units) >= 0 else ''}{len(player.centers) - len(player.units)})"
    return response, None


@perms.gm("edit")
def edit(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    return parse_edit_state(ctx.message.content, manager.get_board(ctx.guild.id))


@perms.gm("create a game")
def create_game(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    return manager.create_game(ctx.guild.id), None


@perms.gm("unlock orders")
def enable_orders(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = True
    return "Successful", None


@perms.gm("lock orders")
def disable_orders(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = False
    return "Successful", None


def info(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    out = "Phase: " + str(board.phase) + "\nOrders are: " + ("Open" if board.orders_enabled else "Locked")
    return out, None


def province_info(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
    board = manager.get_board(ctx.guild.id)
    province_name = ctx.message.content.removeprefix(".province_info ").strip()
    if not province_name:
        raise ValueError("Usage: .province_info <province>")
    province = board.get_province(province_name)
    if province is None:
        raise ValueError(f"Could not find province {province_name}")
    # fmt: off
    out = f"Province: {province.name}\n" + \
        f"Type: {province.type.name}\n" + \
        f"Coasts: {len(province.coasts)}\n" + \
        f"Owner: {province.owner.name if province.owner else 'None'}\n" + \
        f"Unit: {(province.unit.player.name + ' ' + province.unit.unit_type.name) if province.unit else 'None'}\n" + \
        f"Center: {province.has_supply_center}\n" + \
        f"Core: {province.core.name if province.core else 'None'}\n" + \
        f"Half-Core: {province.half_core.name if province.half_core else 'None'}\n" + \
        f"Adjacent Provinces:\n- " + "\n- ".join(sorted([adjacent.name for adjacent in province.adjacent])) + "\n"
    # fmt: on
    return out, None
