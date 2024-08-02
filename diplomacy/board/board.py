from typing import List, Set, Tuple, Mapping

from config import players
from diplomacy.phase import spring_moves
from diplomacy.player import Player
from diplomacy.province import Province
from diplomacy.unit import Unit


class Board:
    def __init__(self, provinces: List[Province], adjacencies: Set[Tuple[str, str]]):
        self.provinces = provinces
        self.adjacencies = adjacencies

        self.players = set()
        units = get_units(provinces)
        for name in players:
            self.players.add(Player(name, units[name]))

        self.phase = spring_moves


def get_units(provinces: List[Province]) -> Mapping[str, Set[Unit]]:
    unit_map = {}
    for province in provinces:
        unit = province.unit
        if unit is None:
            continue

        player = unit.player
        if player not in unit_map:
            unit_map[player] = set()

        unit_map[player].add(unit)
    return unit_map
