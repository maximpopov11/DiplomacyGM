from discord.ext import commands

from bot.config import gm_roles, gm_channels, player_channel_suffix
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.order import Order
from diplomacy.persistence.phase import Phase, winter_builds
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType, Unit

whitespace_dict = {
    "_",
}

_north_coast = "north coast"
_south_coast = "south coast"
_east_coast = "east coast"
_west_coast = "west coast"

coast_dict = {
    _north_coast: ["nc", "north coast"],
    _south_coast: ["sc", "south coast"],
    _east_coast: ["ec", "east coast"],
    _west_coast: ["wc", "west coast"],
}

_army = "army"
_fleet = "fleet"

unit_dict = {
    _army: ["a", "army", "cannon"],
    _fleet: ["f", "fleet", "boat", "ship"],
}

_spring_moves = "spring moves"
_spring_retreats = "spring retreats"
_fall_moves = "fall moves"
_fall_retreats = "fall retreats"
_winter_builds = "winter builds"


def is_gm(author: commands.Context.author) -> bool:
    for role in author.roles:
        if role.name in gm_roles:
            return True
    return False


def is_gm_channel(channel: commands.Context.channel) -> bool:
    return channel.name in gm_channels


def get_player_by_role(author: commands.Context.author, manager: Manager, server_id: int) -> Player | None:
    for role in author.roles:
        for player in manager.get_board(server_id).players:
            if player.name == role.name:
                return player
    return None


def is_player_channel(player_role: str, channel: commands.Context.channel) -> bool:
    player_channel = player_role.lower() + player_channel_suffix
    return player_channel == channel.name


def get_keywords(command: str) -> list[str]:
    """Command is split by whitespace with '_' representing whitespace in a concept to be stuck in one word.
    e.g. 'A New_York - Boston' becomes ['A', 'New York', '-', 'Boston']"""
    keywords = command.split(" ")
    for keyword in keywords:
        for i in range(len(keyword)):
            if keyword[i] in whitespace_dict:
                keyword = keyword[:i] + " " + keyword[i + 1 :]
    return keywords


# TODO: (ALPHA): people want to input coasts in different ways, we should support that by using this on location suffix
def _get_coast_signature(string: str) -> str | None:
    if string in coast_dict[_north_coast]:
        return "nc"
    elif string in coast_dict[_south_coast]:
        return "sc"
    elif string in coast_dict[_east_coast]:
        return "ec"
    elif string in coast_dict[_west_coast]:
        return "wc"
    else:
        return None


def get_unit_type(command: str) -> UnitType | None:
    for word in command:
        if word in unit_dict[_army]:
            return UnitType.ARMY
        if word in unit_dict[_fleet]:
            return UnitType.FLEET
    return None


def get_phase(command: str) -> Phase | None:
    if _spring_moves in command:
        return phase.spring_moves
    elif _spring_retreats in command:
        return phase.spring_retreats
    elif _fall_moves in command:
        return phase.fall_moves
    elif _fall_retreats in command:
        return phase.fall_retreats
    elif _winter_builds in command:
        return phase.winter_builds
    else:
        return None


def get_orders(board: Board, player_restriction: Player | None) -> str:
    if board.phase == winter_builds:
        for player in board.players:
            if not player_restriction or player == player_restriction:
                response = "Received orders:"
                for order in player.build_orders:
                    response += f"\n{order}"
    else:
        orders: list[Order] = []
        missing: list[Unit] = []

        for unit in board.units:
            if not player_restriction or unit.player == player_restriction:
                order = unit.order
                if order:
                    orders.append(order)
                else:
                    missing.append(unit)

        response = ""
        if missing:
            response += "Missing orders:"
            for unit in missing:
                response += f"\n{unit}"
            response += "\n"
        if orders:
            response += "Submitted orders:"
            for order in orders:
                response += f"\n{order}"
        return response
