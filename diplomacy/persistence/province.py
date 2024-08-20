from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diplomacy.persistence.player import Player
    from diplomacy.persistence.unit import Unit


class ProvinceType(Enum):
    LAND = 1
    ISLAND = 2
    SEA = 3


class Province:
    def __init__(
        self,
        name: str,
        coordinates: list[tuple[float, float]],
        province_type: ProvinceType,
        has_supply_center: bool,
        core: Player | None,
        owner: Player | None,
        unit: Unit | None,
    ):
        self.name: str = name
        self.coordinates: list[tuple[float, float]] = coordinates
        self.type: ProvinceType = province_type
        self.has_supply_center: bool = has_supply_center
        self.core: Player | None = core
        self.half_core: Player | None = None
        self.owner: Player | None = owner
        self.unit: Unit | None = unit
        self.dislodged_unit: Unit | None = None

        # these will be set shortly after initialization
        self.adjacent: set[Province] = set()
        self.coasts: set[Coast] = set()

    def set_adjacent(self, provinces: set[Province]) -> None:
        self.adjacent = provinces

    def set_coasts(self):
        """This should only be called once all province adjacencies have been set."""
        if self.type == ProvinceType.SEA:
            # seas don't have coasts
            return set()

        sea_provinces = self.adjacent.copy()
        for province in sea_provinces:
            # Islands do not break coasts
            if province.type != ProvinceType.SEA and province.type != ProvinceType.ISLAND:
                sea_provinces.remove(province)

        if len(sea_provinces) == 0:
            # this is not a coastal province
            return set()

        coast_sets: list[set[Province]] = []
        while sea_provinces:
            coast_set: set[Province] = set()
            to_parse: list[Province] = [sea_provinces.pop()]
            while to_parse:
                province = to_parse.pop()
                coast_set.add(province)
                sea_provinces.remove(province)
                for adjacent in province.adjacent:
                    to_parse.append(adjacent)
            coast_sets.append(coast_set)

        for i, coast_set in enumerate(coast_sets):
            name = f"{self.name} coast #{i}"
            self.coasts.add(Coast(name, coast_set))


class Coast:
    def __init__(self, name: str, adjacent_seas: set[Province]):
        """name should be "<province_name> coast #<x>" with unique <x> for each coast in this province"""
        self.name: str = name
        self.adjacent_seas: set[Province] = adjacent_seas
