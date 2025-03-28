import asyncio
import io
import os
import zipfile
import discord
from discord.ext import commands

from bot import config

from diplomacy.adjudicator.utils import svg_to_png
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType, Unit

whitespace_dict = {
    "_",
}

_north_coast = "nc"
_south_coast = "sc"
_east_coast = "ec"
_west_coast = "wc"

coast_dict = {
    _north_coast: ["nc", "north coast", "(nc)"],
    _south_coast: ["sc", "south coast", "(sc)"],
    _east_coast: ["ec", "east coast", "(ec)"],
    _west_coast: ["wc", "west coast", "(wc)"],
}

_army = "army"
_fleet = "fleet"

unit_dict = {
    _army: ["a", "army", "cannon"],
    _fleet: ["f", "fleet", "boat", "ship"],
}

discord_message_limit = 2000
discord_file_limit = 10 * (2**20)

def is_admin(author: commands.Context.author) -> bool:
    return author.name in ["eebopmasch", "icecream_guy", "_bumble", "thisisflare", "eelisha"]


def is_gm(author: commands.Context.author) -> bool:
    for role in author.roles:
        if config.is_gm_role(role.name):
            return True
    return False


def is_gm_channel(channel: commands.Context.channel) -> bool:
    return config.is_gm_channel(channel.name) and config.is_gm_category(channel.category.name)


def get_player_by_role(author: commands.Context.author, manager: Manager, server_id: int) -> Player | None:
    for role in author.roles:
        for player in manager.get_board(server_id).players:
            if player.name == role.name:
                return player
    return None


def get_player_by_channel(channel: commands.Context.channel, manager: Manager, server_id: int) -> Player | None:
    name = channel.name
    if not name.endswith(config.player_channel_suffix) or not config.is_player_category(channel.category.name):
        return None
    name = name[: -(len(config.player_channel_suffix))]
    return get_player_by_name(name, manager, server_id)


def get_player_by_name(name: str, manager: Manager, server_id: int) -> Player | None:
    for player in manager.get_board(server_id).players:
        if player.name.lower() == name.strip().lower():
            return player
    return None


def is_player_channel(player_role: str, channel: commands.Context.channel) -> bool:
    player_channel = player_role.lower() + config.player_channel_suffix
    return player_channel == channel.name and config.is_player_category(channel.category.name)


def get_keywords(command: str) -> list[str]:
    """Command is split by whitespace with '_' representing whitespace in a concept to be stuck in one word.
    e.g. 'A New_York - Boston' becomes ['A', 'New York', '-', 'Boston']"""
    keywords = command.split(" ")
    for i in range(len(keywords)):
        for j in range(len(keywords[i])):
            if keywords[i][j] in whitespace_dict:
                keywords[i] = keywords[i][:j] + " " + keywords[i][j + 1 :]

    for i in range(len(keywords)):
        keywords[i] = _manage_coast_signature(keywords[i])

    return keywords


def _manage_coast_signature(keyword: str) -> str:
    for coast_key, coast_val in coast_dict.items():
        # we want to make sure this was a separate word like "zapotec ec" and not part of a word like "zapotec"
        suffix = f" {coast_val}"
        if keyword.endswith(suffix):
            # remove the suffix
            keyword = keyword[: len(keyword) - len(suffix)]
            # replace the suffix with the one we expect
            new_suffix = f" {coast_key}"
            keyword += f" {new_suffix}"
    return keyword


def get_unit_type(command: str) -> UnitType | None:
    command = command.strip()
    if command in unit_dict[_army]:
        return UnitType.ARMY
    if command in unit_dict[_fleet]:
        return UnitType.FLEET
    return None

async def send_message_and_file(channel: commands.Context.channel, message: str, file: str, file_name: str):
    if message:
        while discord_message_limit < len(message):
            # Try to find an even line break to split the message on
            cutoff = message.rfind("\n", 0, discord_message_limit)
            if cutoff == -1:
                cutoff = discord_message_limit
            await channel.send(message[:cutoff].strip())
            message = message[cutoff:].strip()
    if file is not None and len(file) > discord_file_limit:
        # zip compression without using files (disk is slow)

        # We create a virtual file, write to it, and then restart it
        # for some reason zipfile doesn't support this natively
        with io.BytesIO() as vfile:
            zip_file = zipfile.ZipFile(vfile, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=9)
            zip_file.writestr(f"{file_name}", file, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            zip_file.close()
            vfile.seek(0)
            await channel.send(message, file=discord.File(fp=vfile, filename=f"{file_name}.zip"))
    elif file is not None:
        with io.BytesIO(file) as vfile:
            await channel.send(message, file=discord.File(fp=vfile, filename=f"{file_name}"))
    elif message is not None and len(message) > 0:
        await channel.send(message)


def get_orders(board: Board, player_restriction: Player | None) -> str:
    if phase.is_builds(board.phase):
        response = "Received orders:"
        for player in sorted(board.players, key=lambda sort_player: sort_player.name):
            if not player_restriction or player == player_restriction:
                response += f"\n**{player.name}**: ({len(player.centers)}) ({'+' if len(player.centers) - len(player.units) >= 0 else ''}{len(player.centers) - len(player.units)})"
                for unit in player.build_orders:
                    response += f"\n{unit}"
        return response
    else:

        if player_restriction is None:
            players = board.players
        else:
            players = {player_restriction}

        response = ""

        for player in sorted(players, key=lambda p: p.name):
            if phase.is_retreats(board.phase):
                in_moves = lambda u: u == u.province.dislodged_unit
            else:
                in_moves = lambda _: True
            moving_units = [unit for unit in player.units if in_moves(unit)]
            ordered = [unit for unit in moving_units if unit.order is not None]
            missing = [unit for unit in moving_units if unit.order is None]

            response += f"**{player.name}** ({len(ordered)}/{len(moving_units)})\n"
            if missing:
                response += f"__Missing Orders:__\n"
                for unit in sorted(missing, key=lambda _unit: _unit.province.name):
                    response += f"{unit}\n"
            if ordered:
                response += f"__Submitted Orders:__\n"
                for unit in sorted(ordered, key=lambda _unit: _unit.province.name):
                    response += f"{unit} {unit.order}\n"

        return response


def get_filtered_orders(board: Board, player_restriction: Player) -> str:
    visible = board.get_visible_provinces(player_restriction)
    if phase.is_builds(board.phase):
        response = ""
        for player in sorted(board.players, key=lambda sort_player: sort_player.name):
            if not player_restriction or player == player_restriction:
                visible = [order for order in player.build_orders if order.location.as_province() in visible]

                if len(visible) > 0:
                    response += f"\n**{player.name}**: ({len(player.centers)}) ({'+' if len(player.centers) - len(player.units) >= 0 else ''}{len(player.centers) - len(player.units)})"
                    for unit in visible:
                        response += f"\n{unit}"
        return response
    else:
        response = ""

        for player in board.players:
            if phase.is_retreats(board.phase):
                in_moves = lambda u: u == u.province.dislodged_unit
            else:
                in_moves = lambda _: True
            moving_units = [unit for unit in player.units if in_moves(unit) and unit.province in visible]

            if len(moving_units) > 0:
                ordered = [unit for unit in moving_units if unit.order is not None]
                missing = [unit for unit in moving_units if unit.order is None]

                response += f"**{player.name}** ({len(ordered)}/{len(moving_units)})\n"
                if missing:
                    response += f"__Missing Orders:__\n"
                    for unit in sorted(missing, key=lambda _unit: _unit.province.name):
                        response += f"{unit}\n"
                if ordered:
                    response += f"__Submitted Orders:__\n"
                    for unit in sorted(ordered, key=lambda _unit: _unit.province.name):
                        response += f"{unit} {unit.order}\n"

        return response
    
svg_export_limit = asyncio.Semaphore(int(os.getenv("simultaneous_svg_exports_limit")))

async def convert_svg_and_send_file(channel, message, file, file_name):
    async with svg_export_limit:
        file, file_name = await svg_to_png(file, file_name)
        await send_message_and_file(channel, message, file, file_name)
