import re
import logging
import time

from bot.sanitize import sanitize_name
from diplomacy.persistence.phase import Phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, ProvinceType, Coast, Location, get_adjacent_provinces
from diplomacy.persistence.unit import Unit, UnitType

logger = logging.getLogger(__name__)


class Board:
    def __init__(
        self, players: set[Player], provinces: set[Province], units: set[Unit], phase: Phase, data, datafile: str, fow: bool, year_offset: int = 1642
    ):
        self.players: set[Player] = players
        self.provinces: set[Province] = provinces
        self.units: set[Unit] = units
        self.phase: Phase = phase
        self.year = 0
        self.year_offset = year_offset
        self.board_id = 0
        self.fish = 0
        self.fish_pop = {
            "fish_pop": float(700),
            "time": time.time()
        }
        self.orders_enabled: bool = True
        self.data: dict = data
        self.datafile = datafile
        self.name = None
        self.fow = fow

        # store as lower case for user input purposes
        self.name_to_player: dict[str, Player] = {player.name.lower(): player for player in self.players}
        # remove periods and apostrophes
        self.cleaned_name_to_player: dict[str, Player] = {sanitize_name(player.name.lower()): player for player in self.players}
        self.name_to_province: dict[str, Province] = {}
        self.name_to_coast: dict[str, Coast] = {}
        for location in self.provinces:
            self.name_to_province[location.name.lower()] = location
            for coast in location.coasts:
                self.name_to_coast[coast.name.lower()] = coast

    def get_player(self, name: str) -> Player:
        if name.lower() == "none":
            return None
        if name.lower() not in self.name_to_player:
            raise ValueError(f"Player {name} not found")
        return self.name_to_player.get(name.lower())

    def get_cleaned_player(self, name: str) -> Player:
        if name.lower() == "none":
            return None
        if name.lower() not in self.cleaned_name_to_player:
            raise ValueError(f"Player {name} not found")
        return self.cleaned_name_to_player.get(sanitize_name(name.lower()))


    # TODO: break ties in a fixed manner
    def get_players_by_score(self) -> list[Player]:
        return sorted(self.players, key=lambda sort_player: (-sort_player.score(), sort_player.name.lower()))

    def get_players_by_points(self) -> list[Player]:
        return sorted(self.players, key=lambda sort_player: (-sort_player.points, -len(sort_player.centers), sort_player.name.lower()))

    # TODO: this can be made faster if necessary
    def get_province(self, name: str) -> Province:
        province, _ = self.get_province_and_coast(name)
        return province

    def get_province_and_coast(self, name: str) -> tuple[Province, Coast | None]:
        # FIXME: This should not be raising exceptions many places already assume it returns None on failure.
        # TODO: (BETA) we build this everywhere, let's just have one live on the Board on init
        # we ignore capitalization because this is primarily used for user input
        # People input apostrophes that don't match what the province names are
        name = re.sub(r"[‘’`´′‛]", "'", name)
        name = name.lower()
        if "abbreviations" in self.data and name in self.data["abbreviations"]:
            name = self.data["abbreviations"][name].lower()
        coast = self.name_to_coast.get(name)
        if coast:
            return coast.province, coast
        elif name in self.name_to_province:
            return self.name_to_province[name], None

        # failed to match, try to get possible locations
        potential_locations = self.get_possible_locations(name)
        if len(potential_locations) > 5:
            raise Exception(f"The location {name} is ambiguous. Please type out the full name.")
        elif len(potential_locations) > 1:
            raise Exception(
                f'The location {name} is ambiguous. Possible matches: {", ".join([loc.name for loc in potential_locations])}.'
            )
        elif len(potential_locations) == 0:
            raise Exception(f"The location {name} does not match any known provinces.")
        else:
            location = potential_locations[0]
            if isinstance(location, Coast):
                return location.province, location
            elif isinstance(location, Province):
                return location, None
            else:
                raise Exception(f"Unknown issue occurred when attempting to find the location {name}.")

    def get_visible_provinces(self, player: Player) -> set[Province]:
        visible: set[Province] = set()
        for province in self.provinces:
            for unit in player.units:
                if unit.unit_type == UnitType.ARMY:
                    if province in get_adjacent_provinces(unit.province) and province.type != ProvinceType.SEA:
                        visible.add(province)
                if unit.unit_type == UnitType.FLEET:
                    if (unit.coast and province in get_adjacent_provinces(unit.coast)) or (not unit.coast and province in get_adjacent_provinces(unit.province)):
                        visible.add(province)

        for unit in player.units:
            visible.add(unit.province)

        for province in player.centers:
            if province.core == player:
                visible.update(province.adjacent)
            visible.add(province)

        return visible

    def get_possible_locations(self, name: str) -> list[Province]:
        pattern = r"^{}.*$".format(re.escape(name.strip()).replace("\\ ", r"\S*\s*"))
        matches = []
        for province in self.provinces:
            if re.search(pattern, province.name.lower()):
                matches.append(province)
            else:
                matches += [coast for coast in province.coasts if re.search(pattern, coast.name.lower())]
        return matches

    def get_location(self, name: str) -> Location:
        # People input apostrophes that don't match what the province names are
        name = re.sub(r"[‘’`´′‛]", "'", name)
        province, coast = self.get_province_and_coast(name)

        if coast:
            return coast
        return province

    def get_build_counts(self) -> list[tuple[str, int]]:
        build_counts = []
        for player in self.players:
            build_counts.append((player.name, len(player.centers) - len(player.units)))
        build_counts = sorted(build_counts, key=lambda counts: counts[1])
        return build_counts

    def get_phase_and_year_string(self):
        return f"{self.year} {self.phase.name}"

    def change_owner(self, province: Province, player: Player):
        if province.has_supply_center:
            if province.owner:
                province.owner.centers.remove(province)
            if player:
                player.centers.add(province)
        province.owner = player

    def create_unit(
        self,
        unit_type: UnitType,
        player: Player,
        province: Province,
        coast: Coast | None,
        retreat_options: set[Province] | None,
    ) -> Unit:
        unit = Unit(unit_type, player, province, coast, retreat_options)
        if retreat_options is not None:
            if province.dislodged_unit:
                raise RuntimeError(f"{province.name} already has a dislodged unit")
            province.dislodged_unit = unit
        else:
            if province.unit:
                raise RuntimeError(f"{province.name} already has a unit")
            province.unit = unit
        player.units.add(unit)
        self.units.add(unit)
        return unit

    def move_unit(self, unit: Unit, new_location: Location) -> Unit:
        new_province = new_location
        new_coast = None
        if isinstance(new_location, Coast):
            new_province = new_location.province
            new_coast = new_location

        if new_province.unit:
            raise RuntimeError(f"{new_province.name} already has a unit")
        new_province.unit = unit
        unit.province.unit = None
        unit.province = new_province
        unit.coast = new_coast
        return unit

    def delete_unit(self, province: Province) -> Unit:
        unit = province.unit
        province.unit = None
        unit.player.units.remove(unit)
        self.units.remove(unit)
        return unit

    def delete_dislodged_unit(self, province: Province) -> Unit:
        unit = province.dislodged_unit
        province.dislodged_unit = None
        unit.player.units.remove(unit)
        self.units.remove(unit)
        return unit

    def delete_all_units(self) -> None:
        for unit in self.units:
            unit.province.unit = None

        for player in self.players:
            player.units = set()

        self.units = set()

    def delete_dislodged_units(self) -> None:
        dislodged_units = set()
        for unit in self.units:
            if unit.retreat_options:
                dislodged_units.add(unit)

        for unit in dislodged_units:
            unit.province.dislodged_unit = None
            unit.player.units.remove(unit)
            self.units.remove(unit)

    def clear_failed_orders(self) -> None:
        for unit in self.units:
            unit.province.unit = None

        for player in self.players:
            player.units = set()

        self.units = set()

    def get_year_int(self) -> int:
        return self.year_offset + self.year

    @staticmethod
    def convert_year_int_to_str(year: int) -> str:
        # No 0 AD / BC
        if year <= 0:
            return f"{str(1-year)} BC"
        else:
            return str(year)

    def get_year_str(self) -> str:
        return self.convert_year_int_to_str(self.get_year_int())
        
    def is_chaos(self) -> bool:
        return self.data["players"] == "chaos"
