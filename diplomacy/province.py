from __future__ import annotations

from enum import Enum
from typing import List, NoReturn, Optional, Set, Tuple, TYPE_CHECKING

from diplomacy.player import Player

if TYPE_CHECKING:
    from diplomacy.unit import Unit


class ProvinceType(Enum):
    LAND = 1
    SEA = 2


# TODO: (MAP) check that we set all province values in vector map parsing (owners, cores, etc.)
class Province:
    def __init__(self, coordinates: List[Tuple[float, float]], province_type: ProvinceType):
        self.coordinates: List[Tuple[float, float]] = coordinates

        # TODO: (BETA) setting everything in initialization would be cool, needs a bit more prep on the gathering side
        # will be set later, needs defined province coordinates first
        self.name: str = ""
        self.type: ProvinceType = province_type
        self.has_supply_center: bool = False
        self.coasts: Set[Coast] = set()
        self.adjacent: Set[Province] = set()
        self.core: Optional[Player] = None
        self.half_core: Optional[Player] = None
        self.owner: Optional[Player] = None
        self.unit: Optional[Unit] = None

    def set_name(self, name) -> NoReturn:
        # TODO: (MAP) don't need this anymore, can set immediately
        self.name = name

    def set_adjacent(self, provinces: Set[Province]) -> NoReturn:
        self.adjacent = provinces
        # TODO: (MAP) include sea provinces (awaiting GM fill file)
        # TODO: (MAP) set coasts (awaiting GM fill file)

    def set_has_supply_center(self, val: bool) -> NoReturn:
        self.has_supply_center = val

    def set_unit(self, unit: Unit) -> NoReturn:
        self.unit = unit


class Coast:
    def __init__(
        self,
        name: str,
        adjacent_seas: Set[Province],
        adjacent_coasts: Tuple[Coast, Coast],
    ):
        # the name should be "<province_name> coast #<x>" with unique <x> for each coast in this province
        self.name: str = name
        self.adjacent_seas: Set[Province] = adjacent_seas
        self.adjacent_coasts: Tuple[Coast, Coast] = adjacent_coasts
