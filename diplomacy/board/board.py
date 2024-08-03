from typing import Mapping, Set

from config import players
from diplomacy.phase import Phase, spring_moves
from diplomacy.player import Player
from diplomacy.province import Province
from diplomacy.unit import Unit


# TODO: (1) support high seas/sands via manual input for alphabot
class Board:
    def __init__(self, provinces: Set[Province]):
        self.provinces: Set[Province] = provinces

        self.players: Set[Player] = set()
        centers = get_centers(provinces)
        units = get_units(provinces)
        for name in players:
            self.players.add(Player(name, centers[name], units[name]))

        self.phase: Phase = spring_moves


def get_centers(provinces: Set[Province]) -> Mapping[str, Set[Province]]:
    center_map = {}
    for province in provinces:
        if province.has_supply_center:
            player = province.owner.name
            if player not in center_map:
                center_map[player] = set()
            center_map[player].add(province)
    return center_map


def get_units(provinces: Set[Province]) -> Mapping[str, Set[Unit]]:
    unit_map = {}
    for province in provinces:
        unit = province.unit
        if unit is None:
            continue

        player = unit.player.name
        if player not in unit_map:
            unit_map[player] = set()

        unit_map[player].add(unit)
    return unit_map
