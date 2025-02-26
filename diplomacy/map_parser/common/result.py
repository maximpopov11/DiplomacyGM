import copy
import logging
from diplomacy.persistence.board import Board
from diplomacy.persistence.phase import Phase, initial
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Coast, Province
from diplomacy.persistence.unit import Unit

logger = logging.getLogger(__name__)

def copyset[T](m: dict[T,T], s: set[T]) -> set[T]:
    return {m[x] for x in s}

class ParserResult:
    def __init__(self, players, provinces, units, phase, data, datafile: str):
        # partially instantiated players, provinces, units
        self.players: set[Player] = players
        self.provinces: set[Province] = provinces
        self.units: set[Unit] = units

        # (name, set of (coast name, coast adjacencies))
        self.coast_overrides: set[tuple[str, set[tuple[str, set[str]]]]] = set()

        self.adjacencies: set[tuple[Province, Province]] = set()

        self.phase = phase
        self.data = data
        self.datafile = datafile

        self.province_to_owner: dict[Province, Player] = {}

    def add_province(self, province: Province) -> set[Province]:
        if self.name_to_province.get(province.name) != None:
            raise ValueError(f"Duplicate province {province.name}")

        self.provinces.add(province)
        self.name_to_province[province.name] = province

    # deepcopy and re-link all references manually
    def make_board(self) -> Board:
        player_map: dict[Player, Player] = {}
        province_map: dict[Province, Province] = {}
        unit_map: dict[Unit, Unit] = {}
        coast_map: dict[Coast, Coast] = {}

        for player in self.players:
            player_map[player] = copy.copy(player)

        for province in self.provinces:
            province_map[province] = copy.copy(province)

        for unit in self.units:
            unit_map[unit] = copy.copy(unit)

        for old, new in player_map.items():
            new.centers = copyset(province_map, old.centers)
            new.units = copyset(unit_map, old.units)

        for old, new in province_map.items():
            new.adjacent = copyset(province_map, old.adjacent)
            new_coasts = set()
            for coast in old.coasts:
                new_coast = Coast(coast.name, coast.primary_unit_coordinate, coast.retreat_unit_coordinate,
                                     copyset(province_map, coast.adjacent_seas), province_map[coast.province])
                coast_map[coast] = new_coast
                new_coasts.add(new_coast)

            new.coast = new_coasts

            if old.core != None:
                new.core = player_map[old.core]
            if old.owner != None:
                new.owner = player_map[old.owner]
            if old.unit != None:
                new.unit = unit_map[old.unit]

            assert old.corer == None
            assert old.dislodged_unit == None

        for old, new in unit_map.items():
            new.player = player_map[old.player]
            new.province = province_map[old.province]
            if old.coast != None:
                new.coast = coast_map[old.coast]

            assert old.retreat_options == None
            assert old.order == None

        new_provinces = set()
        for province in province_map.values():
            new_provinces.add(province)

        for province in self.provinces:
            province.adjacent = None

        return Board(set(player_map.values()), set(province_map.values()), set(unit_map.values()), self.phase, self.data, self.datafile)