from typing import List, Set, Tuple, Mapping

from config import players
from diplomacy.phase import spring_moves, Phase
from diplomacy.player import Player
from diplomacy.province import Province
from diplomacy.unit import Unit


# TODO: (1) support high seas/sands via manual input for alphabot
class Board:
    def __init__(self, provinces: Set[Province]):
        self.provinces: Set[Province] = provinces

        self.players: Set[Player] = set()
        units: Set[Unit] = get_units(provinces)
        for name in players:
            self.players.add(Player(name, player_centers, units[name]))

        self.phase: Phase = spring_moves


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
