import asyncio
import logging
import os
import random
from random import randrange
from typing import Callable

from black.trans import defaultdict
from discord import Guild, Role
from discord import PermissionOverwrite
from discord.ext import commands

from bot import config
import bot.perms as perms
from bot.config import is_bumble, temporary_bumbles, ERROR_COLOUR
from bot.parse_edit_state import parse_edit_state
from bot.parse_order import parse_order, parse_remove_order
from bot.utils import (convert_svg_and_send_file, get_filtered_orders, get_orders,
                       get_player_by_channel, get_player_by_channel, is_admin, send_message_and_file,
                       get_role_by_player)
from diplomacy.adjudicator.utils import svg_to_png
from diplomacy.persistence import phase
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.order import Build, Disband
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province

import re

logger = logging.getLogger(__name__)

ping_text_choices = [
    "proudly states",
    "fervently believes in the power of",
    "is being mind controlled by",
]


async def ping(ctx: commands.Context, _: Manager) -> dict[str, ...]:
    response = "Beep Boop"
    if random.random() < 0.1:
        author = ctx.message.author
        content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        if content == "":
            content = " nothing"
        name = author.nick
        if not name:
            name = author.name
        response = name + " " + random.choice(ping_text_choices) + content
    return {"title": response }


async def bumble(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    list_of_bumble = list("bumble")
    random.shuffle(list_of_bumble)
    word_of_bumble = "".join(list_of_bumble)

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
    return {"message": f"**{word_of_bumble}**" }


async def fish(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
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
                return ""
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

    return {"message": fish_message }


async def phish(ctx: commands.Context, _: Manager) -> dict[str, ...]:
    message = "No! Phishing is bad!"
    if is_bumble(ctx.author.name):
        message = "Please provide your firstborn pet and your soul for a chance at winning your next game!"
    return {"message": message }


async def cheat(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
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
                f"{random.choice(list(board.players)).name} is in a perfect position to stab {author}",
                ".bumble",
            ]
        )
        message = f'Here\'s a helpful message I stole from the spectator chat: \n"{sample}"'
    return {"message": message }


async def advice(ctx: commands.Context, _: Manager) -> dict[str, ...]:
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
                "Ambrosius advises taking the opportunity you've been considering, for more will ensue.",
                "The GMs suggest you input your orders so they don't need to hound you for them at the deadline.",
            ]
        )
    return {"message": message }


@perms.gm("botsay")
async def botsay(ctx: commands.Context, _: Manager) -> dict[str, ...]:
    # noinspection PyTypeChecker
    if len(ctx.message.channel_mentions) == 0:
        return {"message": "No Channel Given"}
    channel = ctx.message.channel_mentions[0]
    content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
    content = content.replace(channel.mention, "").strip()
    if len(content) == 0:
        return {"message": "No Message Given"}
    await ctx.message.add_reaction("👍")
    logger.info(f"{ctx.message.author.name} asked me to say '{content}' in {channel.name}")
    return {"channel": channel, "message": content}

@perms.admin("send a GM announcement")
async def announce(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    await ctx.message.add_reaction("👍")
    servers = {ctx.bot.get_guild(server_id) for server_id in manager.list_servers()}
    content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip()
    logger.info(f"{ctx.message.author.name} sent announcement '{content}'")
    message = "Annoucement sent to:"
    for server in servers:
        if server is None:
            continue
        admin_chat_channel = next(channel for channel in server.channels if is_gm_channel(channel))
        if admin_chat_channel is None:
            continue
        message += f"\n- {server.name}"
        await admin_chat_channel.send(f"__Announcement__\n{ctx.message.author.display_name} says:\n{content}")
    return {"message": message}


@perms.player("order")
async def order(player: Player | None, ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)

    if player and not board.orders_enabled:
        return {"message": "Orders locked! If you think this is an error, contact a GM.", "embed_colour": ERROR_COLOUR}

    return parse_order(ctx.message.content, player, board)


@perms.player("remove orders")
async def remove_order(player: Player | None, ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)

    if player and not board.orders_enabled:
        return {"message": "Orders locked! If you think this is an error, contact a GM.", "embed_colour": ERROR_COLOUR}

    content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)

    return parse_remove_order(content, player, board)


@perms.player("view orders")
async def view_orders(player: Player | None, ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    try:
        board = manager.get_board(ctx.guild.id)
        order_text = get_orders(board, player, ctx)
    except RuntimeError as err:
        logger.error(f"View_orders text failed in game with id: {ctx.guild.id}", exc_info=err)
        return {"message": "view_orders text failed", "embed_colour": ERROR_COLOUR}
    return {"title": f"{board.phase.name}" + " " + f"{str(1642 + board.year)}", "message": order_text }


@perms.player("view map")
async def view_map(player: Player | None, ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    return_svg = player or ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip().lower() != "true"
    board = manager.get_board(ctx.guild.id)

    try:
        if not board.fow:
            file, file_name = manager.draw_moves_map(ctx.guild.id, player)
        else:
            file, file_name = manager.draw_fow_players_moves_map(ctx.guild.id, player)
    except Exception as err:
        logger.error(f"View_orders map failed in game with id: {ctx.guild.id}", exc_info=err)
        return {"message": "View_orders map failed" , "embed_colour": ERROR_COLOUR}
    return {
        "title": board.phase.name + " " + str(1642 + board.year),
        "message": "Map created successfully",
        "file": file,
        "file_name": file_name,
        "svg_to_png": return_svg,
        "file_in_embed": False,
    }

@perms.gm("adjudicate")
async def adjudicate(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)

    return_svg = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip().lower() != "true"
    if board.fow:
        await publish_moves(ctx, manager)
        await send_order_logs(ctx, manager)
    manager.adjudicate(ctx.guild.id)

    if board.fow:
        # await publish_current(ctx, manager)
        pass

    if not board.fow:
        file, file_name = manager.draw_current_map(ctx.guild.id)
    else:
        file, file_name = manager.draw_fow_current_map(ctx.guild.id, None)

    return {
        "title": board.phase.name + " " + str(1642 + board.year),
        "message": "Adjudication has completed successfully",
        "file": file,
        "file_name": file_name,
        "svg_to_png": return_svg,
        "file_in_embed": False,
    }

@perms.gm("rollback")
async def rollback(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    return manager.rollback(ctx.guild.id)


@perms.gm("reload")
async def reload(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    return manager.reload(ctx.guild.id)


@perms.gm("remove all orders")
async def remove_all(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)
    for unit in board.units:
        unit.order = None

    database = get_connection()
    database.save_order_for_units(board, board.units)
    return {"message": "Successful" }


async def get_scoreboard(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)

    if board.fow:
        perms.gm_perms_check(ctx, "get scoreboard")

    response = ""
    for player in board.get_players_by_score():

        if (player_role := get_role_by_player(player, ctx.guild.roles)) is not None:
            player_name = player_role.mention
        else:
            player_name = player.name

        response += (f"\n**{player_name}**: "
                     f"{len(player.centers)} ({'+' if len(player.centers) - len(player.units) >= 0 else ''}"
                     f"{len(player.centers) - len(player.units)})")
    return {"title": f"{board.phase.name}" + " " + f"{str(1642 + board.year)}", "message": response }


@perms.gm("edit")
async def edit(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    return parse_edit_state(ctx.message.content, manager.get_board(ctx.guild.id))


@perms.gm("create a game")
async def create_game(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    gametype = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
    if gametype == "":
        gametype = "impdip.json"
    else:
        gametype = gametype.removeprefix(" ") + ".json"
    return {"message": manager.create_game(ctx.guild.id, gametype) }


@perms.gm("unlock orders")
async def enable_orders(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = True
    return {"message": "Successful" }


@perms.gm("lock orders")
async def disable_orders(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)
    board.orders_enabled = False
    return {"message": "Successful" }


@perms.gm("delete the game")
async def delete_game(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    manager.total_delete(ctx.guild.id)
    return {"message": "Game deleted"}

async def info(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    try:
        board = manager.get_board(ctx.guild.id)
    except RuntimeError:
        return {"message": "There is no existing game this this server."}
    return {"message": ("Year: " + str(1642 + board.year) + "\n"
               "Phase: " + str(board.phase) + "\n"
               "Orders are: " + ("Open" if board.orders_enabled else "Locked") + "\n"
               "Fog of War: " + str(board.fow))
            }


async def province_info(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)

    if not board.orders_enabled:
        perms.gm_context_check(ctx, "Orders locked! If you think this is an error, contact a GM.", 
            "You cannot use .province_info in a non-GM channel while orders are locked.")
 
    province_name = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip()
    if not province_name:
        return {"message": "Usage: .province_info <province>"}
    province, coast = board.get_province_and_coast(province_name)
    if province is None:
        return {"message": f"Could not find province {province_name}"}


    # FOW permissions
    if board.fow:
        player = perms.get_player_by_context(ctx, manager, "get province info")
        if player and not province in board.get_visible_provinces(player):
            return {"message": f"Province {province.name} is not visible to you" }
    
    # fmt: off
    if not coast:
        out = f"Province: {province.name}\n" + \
            f"Type: {province.type.name}\n" + \
            f"Coasts: {len(province.coasts)}\n" + \
            f"Owner: {province.owner.name if province.owner else 'None'}\n" + \
            f"Unit: {(province.unit.player.name + ' ' + province.unit.unit_type.name) if province.unit else 'None'}\n" + \
            f"Center: {province.has_supply_center}\n" + \
            f"Core: {province.core.name if province.core else 'None'}\n" + \
            f"Half-Core: {province.half_core.name if province.half_core else 'None'}\n" + \
            f"Adjacent Provinces:\n- " + "\n- ".join(sorted([adjacent.name for adjacent in province.adjacent])) + "\n"
    else:
        coast_unit = None
        if province.unit and province.unit.coast == coast:
            coast_unit = province.unit

        out = f"Province: {coast.name}\n" + \
            "Type: COAST\n" + \
            f"Coast Unit: {(coast_unit.player.name + ' ' + coast_unit.unit_type.name) if coast_unit else 'None'}\n" + \
            f"Province Unit: {(province.unit.player.name + ' ' + province.unit.unit_type.name) if province.unit else 'None'}\n" + \
            "Adjacent Provinces:\n" + \
            "- " + \
            "\n- ".join(sorted([adjacent.name for adjacent in coast.get_adjacent_locations()])) + "\n"
    # fmt: on
    return {"message": out }


@perms.player("view visible provinces")
async def visible_provinces(player: Player | None, ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)

    if not player or not board.fow:
        return {"message": "This command only works for players in fog of war games.", "embed_colour": ERROR_COLOUR}

    visible_provinces = board.get_visible_provinces(player)

    return {"message": ", ".join([x.name for x in visible_provinces])}


async def all_province_data(ctx: commands.Context, manager: Manager) -> dict[str, ...]:
    board = manager.get_board(ctx.guild.id)

    province_by_owner = defaultdict(list)
    for province in board.provinces:
        owner = province.owner
        if not owner:
            owner = "None"
        province_by_owner[owner].append(province.name)

    message = ""
    for owner, provinces in province_by_owner.items():
        message += f"{owner}: "
        for province in provinces:
            message += f"{province}, "
        message += "\n\n"

    return {"message": message }


# needed due to async
from bot.utils import is_gm_channel

# for fog of war
async def publish_current(ctx: commands.Context, manager: Manager):
    await publish_map(ctx, manager, "starting map", lambda m, s, p: m.draw_fow_current_map(s,p))

async def publish_moves(ctx: commands.Context, manager: Manager,):
    await publish_map(ctx, manager, "moves map", lambda m, s, p: m.draw_fow_moves_map(s,p))


async def publish_map(ctx: commands.Context, manager: Manager, name: str, map_caller: Callable[[Manager, int, Player], tuple[str, str]]):
    player_category = None

    guild = ctx.guild
    guild_id = guild.id
    board = manager.get_board(guild_id)


    for category in guild.categories:
        if config.is_player_category(category.name):
            player_category = category
            break

    if not player_category:
        # FIXME this shouldn't be an Error/this should propagate
        raise RuntimeError("No player category found")

    name_to_player: dict[str, Player] = {}
    for player in board.players:
        name_to_player[player.name.lower()] = player

    tasks = []

    for channel in player_category.channels:
        player = get_player_by_channel(channel, manager, guild.id)

        if not player:
            continue

        message = f"Here is the {name} for {board.year + 1642} {board.phase.name}"
        tasks.append(map_publish_task(lambda: map_caller(manager, guild_id, player), channel, message))

    await asyncio.gather(*tasks)

# save at least one svg slot for others
fow_export_limit = asyncio.Semaphore(max(int(os.getenv("simultaneous_svg_exports_limit")) - 1, 1))

async def map_publish_task(map_maker, channel, message):
    async with fow_export_limit:
        file, file_name = map_maker()
        file, file_name = await svg_to_png(file, file_name)
        await send_message_and_file(channel=channel, message=message, file=file, file_name=file_name, file_in_embed=False)

async def send_order_logs(ctx: commands.Context, manager: Manager):
    player_category = None

    guild = ctx.guild
    guild_id = guild.id
    board = manager.get_board(guild_id)

    for category in guild.categories:
        if config.is_player_category(category.name):
            player_category = category
            break

    if not player_category:
        return "No player category found"

    name_to_player: dict[str, Player] = {}
    for player in board.players:
        name_to_player[player.name.lower()] = player
    
    for channel in player_category.channels:
        player = get_player_by_channel(channel, manager, guild.id)

        if not player:
            continue
        
        message = get_filtered_orders(board, player)

        await send_message_and_file(channel=channel, message=message)

    return "Successful"


async def ping_players(ctx: commands.Context, manager: Manager):
    perms.gm_perms_check(ctx, "ping players")

    player_category = None

    timestamp = re.match(r"<t:(\d+):[a-zA-Z]>", ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).strip())
    if timestamp:
        timestamp = f"<t:{timestamp.group(1)}:R>"

    guild = ctx.guild
    guild_id = guild.id
    board = manager.get_board(guild_id)

    for category in guild.categories:
        if config.is_player_category(category.name):
            player_category = category
            break

    if not player_category:
        return {"message": "No player category found", "embed_colour": ERROR_COLOUR }

    name_to_player: dict[str, Player] = {}
    player_to_role: dict[str, Role] = {}
    for player in board.players:
        name_to_player[player.name.lower()] = player
    
    player_roles: set[Role] = set()

    for role in guild.roles:
        if config.is_player_role(role.name):
            player_roles.add(role)

        player = name_to_player.get(role.name.lower())
        if player:
            player_to_role[player] = role

    if len(player_roles) == 0:
        return {"message": "No player role found", "embed_colour": ERROR_COLOUR }

    response = None

    for channel in player_category.channels:
        player = get_player_by_channel(channel, manager, guild.id)

        if not player:
            continue

        role = player_to_role.get(player)
        if not role:
            logger.warning(f"Missing player role for player {player.name} in guild {guild_id}")
            continue

        # Find users which have a player role to not ping spectators
        users = set(filter(lambda m: len(set(m.roles) & player_roles) > 0, role.members))

        if len(users) == 0:
            continue

        if phase.is_builds(board.phase):
            count = len(player.centers) - len(player.units)

            current = 0
            has_disbands = False
            has_builds = False
            for order in player.build_orders:
                if isinstance(order, Disband):
                    current -= 1
                    has_disbands = True
                elif isinstance(order, Build):
                    current += 1
                    has_builds = True

            difference = abs(current-count)
            if difference != 1:
                order_text = "orders"
            else:
                order_text = "order"

            if has_builds and has_disbands:
                response = f"Hey {''.join([u.mention for u in users])}, you have both build and disband orders. Please get this looked at."
            elif count >= 0:
                available_centers = [center for center in player.centers if center.unit == None and center.core == player]
                available = min(len(available_centers), count)

                difference = abs(current - available)
                if current > available:
                    response = f"Hey {''.join([u.mention for u in users])}, you have {difference} more build {order_text} than possible. Please get this looked at."
                elif current < available:
                    response = f"Hey {''.join([u.mention for u in users])}, you have {difference} less build {order_text} than necessary. Make sure that you want to waive."
            elif count < 0:
                if current < count:
                    response = f"Hey {''.join([u.mention for u in users])}, you have {difference} more disband {order_text} than necessary. Please get this looked at."
                elif current > count:
                    response = f"Hey {''.join([u.mention for u in users])}, you have {difference} less disband {order_text} than required. Please get this looked at."
        else:
            if phase.is_retreats(board.phase):
                in_moves = lambda u: u == u.province.dislodged_unit
            else:
                in_moves = lambda _: True

            missing = [unit for unit in player.units if unit.order is None and in_moves(unit)]
            if len(missing) != 1:
                unit_text = "units"
            else:
                unit_text = "unit"

            if missing:
                response = f"Hey **{''.join([u.mention for u in users])}**, you are missing moves for the following {len(missing)} {unit_text}:"
                for unit in sorted(missing, key=lambda _unit: _unit.province.name):
                    response += f"\n{unit}"

        if response:
            if timestamp:
                response += f"\n The orders deadline is {timestamp}."
            await channel.send(response)
            response = None

    return {"message": "Successful" }

async def archive(ctx: commands.Context, _: Manager) -> dict[str, ...]:
    perms.gm_perms_check(ctx, "archive")

    categories = [channel.category for channel in ctx.message.channel_mentions]
    if not categories:
        return {"message": "This channel is not part of a category.", "embed_colour": ERROR_COLOUR}

    for category in categories:
        for channel in category.channels:
            overwrites = channel.overwrites

            # Remove all permissions except for everyone
            overwrites.clear()
            overwrites[ctx.guild.default_role] = PermissionOverwrite(read_messages=True, send_messages=False)

            # Apply the updated overwrites
            await channel.edit(overwrites=overwrites)

    message = f"The following catagories have been archived: {' '.join([catagory.name for catagory in categories])}"
    return {"message": message }
