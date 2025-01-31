from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import TYPE_CHECKING

from shapely import Polygon

if TYPE_CHECKING:
    from diplomacy.persistence import player
    from diplomacy.persistence import unit


class Location:
    def __init__(
        self,
        name: str,
        primary_unit_coordinate: tuple[float, float],
        retreat_unit_coordinate: tuple[float, float],
    ):
        self.all_locs = set()
        self.all_rets = set()
        self.name: str = name
        self.primary_unit_coordinate: tuple[float, float] = primary_unit_coordinate
        self.retreat_unit_coordinate: tuple[float, float] = retreat_unit_coordinate
        if primary_unit_coordinate:
            self.all_locs: set[tuple[float, float]] = {primary_unit_coordinate}
        if retreat_unit_coordinate:
            self.all_rets: set[float[float, float]] = {retreat_unit_coordinate}

    @abstractmethod
    def get_owner(self) -> player.Player | None:
        pass

    @abstractmethod
    def get_unit(self) -> unit.Unit | None:
        pass

    def __str__(self):
        return self.name


class ProvinceType(Enum):
    LAND = 1
    ISLAND = 2
    SEA = 3


class Province(Location):
    def __init__(
        self,
        name: str,
        coordinates: Polygon,
        primary_unit_coordinate: tuple[float, float],
        retreat_unit_coordinate: tuple[float, float],
        province_type: ProvinceType,
        has_supply_center: bool,
        adjacent: set[Province],
        coasts: set[Coast],
        core: player.Player | None,
        owner: player.Player | None,
        local_unit: unit.Unit | None,  # TODO: probably doesn't make sense to init with a unit
    ):
        if primary_unit_coordinate == None:
            primary_unit_coordinate = (0, 0)
        if retreat_unit_coordinate == None:
            retreat_unit_coordinate = (1, 1)
        super().__init__(name, primary_unit_coordinate, retreat_unit_coordinate)
        self.geometry: Polygon = coordinates
        self.type: ProvinceType = province_type
        self.has_supply_center: bool = has_supply_center
        self.adjacent: set[Province] = adjacent
        self.coasts: set[Coast] = coasts
        self.corer: player.Player | None = None
        self.core: player.Player | None = core
        self.half_core: player.Player | None = None
        self.owner: player.Player | None = owner
        self.unit: unit.Unit | None = local_unit
        self.dislodged_unit: unit.Unit | None = None

    def __str__(self):
        return self.name

    def get_owner(self) -> player.Player | None:
        return self.owner

    def get_unit(self) -> unit.Unit | None:
        return self.unit

    def coast(self) -> Coast:
        if len(self.coasts) != 1:
            raise RuntimeError(f"Cannot get coast of a province with num coasts {len(self.coasts)} != 1")
        return next(coast for coast in self.coasts)

    def set_coasts(self):
        """This should only be called once all province adjacencies have been set."""

        # Externally set, i. e. by json_cheats()
        if self.coasts:
            return

        if self.type == ProvinceType.SEA:
            # seas don't have coasts
            return set()

        sea_provinces: set[Province] = set()
        for province in self.adjacent:
            # Islands do not break coasts
            if province.type == ProvinceType.SEA or province.type == ProvinceType.ISLAND:
                sea_provinces.add(province)

        if len(sea_provinces) == 0:
            # this is not a coastal province
            return set()

        # TODO: (BETA) don't hardcode coasts
        coast_sets: list[set[Province]] = []
        if True:
            coast_sets.append(sea_provinces)
        else:
            while sea_provinces:
                coast_set: set[Province] = set()
                to_parse: list[Province] = [next(iter(sea_provinces))]
                while to_parse:
                    province = to_parse.pop()
                    sea_provinces.remove(province)
                    coast_set.add(province)
                    for adjacent in province.adjacent:
                        if (
                            adjacent in self.adjacent
                            and adjacent.type is not ProvinceType.LAND
                            and adjacent not in coast_set
                            and adjacent not in to_parse
                        ):
                            to_parse.append(adjacent)
                coast_sets.append(coast_set)

        for i, coast_set in enumerate(coast_sets):
            name = f"{self.name} coast"
            self.coasts.add(Coast(name, None, None, coast_set, self))


class Coast(Location):
    def __init__(
        self,
        name: str,
        primary_unit_coordinate: tuple[float, float],
        retreat_unit_coordinate: tuple[float, float],
        adjacent_seas: set[Province],
        province: Province,
    ):
        if primary_unit_coordinate == None:
            primary_unit_coordinate = (0, 0)
        if retreat_unit_coordinate == None:
            retreat_unit_coordinate = (1, 1)
        super().__init__(name, primary_unit_coordinate, retreat_unit_coordinate)
        self.adjacent_seas: set[Province] = adjacent_seas
        self.province: Province = province

    def __str__(self):
        return self.name

    def get_owner(self) -> player.Player | None:
        return self.province.get_owner()

    def get_unit(self) -> unit.Unit | None:
        return self.province.get_unit()

    def get_adjacent_coasts(self) -> set[Coast]:
        # TODO: (BETA) this will generate false positives (e.g. mini province keeping 2 big province coasts apart)
        adjacent_coasts: set[Coast] = set()
        if self.province.type == ProvinceType.ISLAND:
            for province2 in self.province.adjacent:
                adjacent_coasts.update(province2.coasts)
            return adjacent_coasts
      
        for province2 in self.province.adjacent:
            for coast2 in province2.coasts:
                if self.adjacent_seas & coast2.adjacent_seas:
                    adjacent_coasts.add(coast2)
        return adjacent_coasts
