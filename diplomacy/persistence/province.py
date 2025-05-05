from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import TYPE_CHECKING
import logging

from shapely import Polygon, MultiPolygon

logger = logging.getLogger(__name__)

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

    @abstractmethod
    def as_province(self) -> Province:
        pass

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"Location {self.name}"


class ProvinceType(Enum):
    LAND = 1
    ISLAND = 2
    SEA = 3
    IMPASSIBLE = 4


class Province(Location):
    def __init__(
        self,
        name: str,
        coordinates: Polygon | MultiPolygon,
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
        super().__init__(name, primary_unit_coordinate, retreat_unit_coordinate)
        self.geometry: Polygon = coordinates
        self.type: ProvinceType = province_type
        self.has_supply_center: bool = has_supply_center
        self.adjacent: set[Province] = adjacent
        self.impassible_adjacent: set[Province] = set()
        self.coasts: set[Coast] = coasts
        self.corer: player.Player | None = None
        self.core: player.Player | None = core
        self.half_core: player.Player | None = None
        self.owner: player.Player | None = owner
        self.unit: unit.Unit | None = local_unit
        self.dislodged_unit: unit.Unit | None = None

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Province {self.name}"

    def get_owner(self) -> player.Player | None:
        return self.owner

    def get_unit(self) -> unit.Unit | None:
        return self.unit
    
    def as_province(self) -> Province:
        return self

    def coast(self) -> Coast:
        if len(self.coasts) != 1:
            raise RuntimeError(f"Cannot get coast of a province with num coasts {len(self.coasts)} != 1")
        return next(coast for coast in self.coasts)

    def set_adjacent(self, other: Province):
        if other.type == ProvinceType.IMPASSIBLE:
            self.impassible_adjacent.add(other)
        else:
            self.adjacent.add(other)

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
        super().__init__(name, primary_unit_coordinate, retreat_unit_coordinate)
        self.adjacent_seas: set[Province] = adjacent_seas
        self.province: Province = province

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Coast {self.name}"

    def get_owner(self) -> player.Player | None:
        return self.province.get_owner()

    def get_unit(self) -> unit.Unit | None:
        return self.province.get_unit()
    
    def as_province(self) -> Province:
        return self.province

    @staticmethod
    def detect_costal_connection(c1: Coast, c2: Coast):
        # multiple possible tripoints could happen if there was a scenario
        # where two canals were blocked from connecting on one side by a land province but not the other
        # or by multiple rainbow-shaped seas
        possible_tripoints = c1.adjacent_seas & c2.adjacent_seas
        for possible_tripoint in possible_tripoints:
            # check for situations where one of the provinces is situated in the other two

            if len(possible_tripoint.adjacent) == 2 or len(c1.province.adjacent) == 2 or len(c2.province.adjacent) == 2:
                return True

            # the algorithm is as follows
            # connect all adjacent to the three provinces as possible
            # if they all connect, they form a ring around forcing connection
            # if not, they must form rings inside and outside, meaning there is no connection
            
            # initialise the process queue and the connection sets
            procqueue: list[Province] = []
            connected_sets: set[frozenset[Province]] = set()

            for adjacent in c1.province.adjacent | c1.province.impassible_adjacent | \
                            c2.province.adjacent | c2.province.impassible_adjacent | \
                            possible_tripoint.adjacent | possible_tripoint.impassible_adjacent:
                if adjacent not in (c1.province, c2.province, possible_tripoint):
                    procqueue.append(adjacent)
                    connected_sets.add(frozenset({adjacent}))
            
            def find_set_with_element(element):
                for subgraph in connected_sets:
                    if element in subgraph:
                        return subgraph
                raise Exception("Error in costal_connection algorithm")

            # we will retain the invariant that no two elements of connected_sets contain the same element
            for to_process in procqueue:
                for neighbor in to_process.adjacent:
                    # going further into or out of rings won't help us
                    if neighbor not in procqueue:
                        continue
                    
                    # Now that we have found two connected subgraphs,
                    # we remove them and merge them
                    this = find_set_with_element(to_process)
                    other = find_set_with_element(neighbor)
                    connected_sets = connected_sets - {this, other}
                    connected_sets.add(this | other)            

            l = 0

            # find connected sets which are adjacent to tripoint and two provinces (so portugal is eliminated from contention if MAO, Gascony, and Spain nc are the locations being tested)
            # FIXME: this leads to false positives
            for candidate in connected_sets:
                needed_neighbors = set([c1.province, c2.province, possible_tripoint])

                for province in candidate:
                    needed_neighbors.difference_update(province.adjacent)

                if len(needed_neighbors) == 0:
                    l += 1

            # If there is 1, that means there was 1 ring (yes)
            # 2, there was two (no)
            # Else, something has gone wrong
            if l == 1:
                return True
            elif l != 2:
                logger.error(f"WARNING: len(connected_sets) should've been 1 or 2, but got {l}.\n"
                            f"hint: between coasts {c1} and {c2}, when looking at mutual sea {possible_tripoint}\n"
                            f"Final state: {connected_sets}")

        # no connection worked
        return False


    def get_adjacent_coasts(self) -> set[Coast]:
        # TODO: (BETA) this will generate false positives (e.g. mini province keeping 2 big province coasts apart)
        adjacent_coasts: set[Coast] = set()
        if self.province.type == ProvinceType.ISLAND:
            for province2 in self.province.adjacent:
                for coast in province2.coasts:
                    if self.province in coast.adjacent_seas:
                        adjacent_coasts.add(coast)
            return adjacent_coasts
      
        for province2 in self.province.adjacent:
            for coast2 in province2.coasts:
                if Coast.detect_costal_connection(self, coast2):
                    adjacent_coasts.add(coast2)
        return adjacent_coasts

    def get_adjacent_locations(self) -> set[Location]:
        return self.adjacent_seas.union(self.get_adjacent_coasts())


def get_adjacent_provinces(location: Location) -> set[Province]:
    if isinstance(location, Coast):
        return location.adjacent_seas | {coast.province for coast in location.get_adjacent_coasts()}
    if isinstance(location, Province):
        return location.adjacent
    raise ValueError(f"Location {location} should be Coast or Province")