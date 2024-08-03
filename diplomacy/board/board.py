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
            center_map.setdefault(province.owner.name, set()).add(province)
    return center_map


def get_units(provinces: Set[Province]) -> Mapping[str, Set[Unit]]:
    unit_map = {}
    for province in provinces:
        if province.unit:
            unit_map.setdefault(province.unit.player.name, set()).add(province.unit)
    return unit_map
