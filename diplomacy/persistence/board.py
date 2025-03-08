import re
import logging

from diplomacy.persistence import phase
from diplomacy.persistence.phase import Phase
from diplomacy.persistence.player import Player, PlayerInfo
from diplomacy.persistence.province import CoastInfo, Province, Coast, Location, ProvinceInfo
from diplomacy.persistence.unit import Unit, UnitInfo, UnitType

logger = logging.getLogger(__name__)

class Board:
    def __init__(
        self, players: set[Player], provinces: set[Province], units: set[Unit], phase: Phase, data, datafile: str
    ):
        self.players: set[Player] = players
        self.provinces: set[Province] = provinces
        self.units: set[Unit] = units
        self.phase: Phase = phase
        self.year = 0
        self.board_id = 0
        self.fish = 0
        self.orders_enabled: bool = True
        self.data = data
        self.datafile = datafile

        self.name_to_players = {(player.name().lower()): player for player in self.players}
        self.name_to_province: dict[str, Province] = {}
        self.name_to_coast: dict[str, Coast] = {}
        for province in self.provinces:
            self.name_to_province[province.name().lower()] = province
            for coast in province.coasts:
                self.name_to_coast[coast.name().lower()] = coast

    # TODO: we could have this as a dict ready on the variant
    def get_player(self, name: str) -> Player | None:
        # we ignore capitalization because this is primarily used for user input
        return self.name_to_players.get(name.lower(), None)

    def get_players_by_score(self) -> list[Player]:
        return sorted(self.players, key=lambda sort_player: sort_player.score(), reverse=True)

    # TODO: we could have this as a dict ready on the variant
    def get_province(self, name: str) -> Province | None:
        # we ignore capitalization because this is primarily used for user input
        return self.name_to_province.get(name.lower(), None)

    def get_province_and_coast(self, name: str) -> tuple[Province, Coast | None]:
        # TODO: (BETA) we build this everywhere, let's just have one live on the Board on init
        # we ignore capitalization because this is primarily used for user input
        name = name.lower()
        coast = self.name_to_coast.get(name)
        if coast:
            return coast.province, coast
        elif name in self.name_to_province:
            return self.name_to_province[name], None
        else:
            return None, None
    
    def get_possible_provinces(self, name: str) -> list[str]:
        pattern = r"\b{}.*".format(name.strip().replace(" ", r".*\b"))
        print(pattern)
        matches = []
        for province in self.provinces:
<<<<<<< HEAD
            if re.search(pattern, province.name.lower()):
                matches.append(province.name)
            else:
                matches += ([coast.name for coast in province.coasts if re.search(pattern, coast.name.lower())])
        return matches
||||||| parent of 22d9793 (fix more)
            province_name = province.name
            similarity = jaro_winkler(name, province_name.lower())

            if similarity > best_similarity:
                best_similarity = similarity
                best_province_name = province_name
        return best_province_name, best_similarity
=======
            province_name = province.name()
            similarity = jaro_winkler(name, province_name.lower())

            if similarity > best_similarity:
                best_similarity = similarity
                best_province_name = province_name
        return best_province_name, best_similarity
>>>>>>> 22d9793 (fix more)

    def get_location(self, name: str) -> Location:
        province, coast = self.get_province_and_coast(name)
        if not province:
            potential_provinces = self.get_possible_provinces(name)
            if len(potential_provinces) > 5:
                raise Exception(f"The province {name} is ambiguous. Please type out the full name.")
            elif len(potential_provinces) > 1:
                raise Exception(f'The province {name} is ambiguous. Possible matches: {", ".join(potential_provinces)}.')
            elif len(potential_provinces) == 0:
                raise Exception(f"The province {name} does not match any known provinces.")
            else:
                full_name = potential_provinces[0]
                province, coast = self.get_province_and_coast(full_name)

        if coast:
            return coast
        return province

    def get_build_counts(self) -> list[tuple[str, int]]:
        build_counts = []
        for player in self.players:
            build_counts.append((player.name(), len(player.centers) - len(player.units)))
        build_counts = sorted(build_counts, key=lambda counts: counts[1])
        return build_counts

    def get_phase_and_year_string(self):
        return f"{self.year} {self.phase.name}"

    def change_owner(self, province: Province, player: Player):
        if province.info.has_supply_center:
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
            province.dislodged_unit = unit
        else:
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
            raise RuntimeError(f"{new_province.name()} already has a unit")
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

class ParserResult:
    def __init__(
        self, player_infos: set[PlayerInfo], province_infos: set[ProvinceInfo], data, datafile: str
    ):
        self.player_infos: set[Player] = player_infos
        self.province_infos = province_infos
        self.data = data
        self.datafile = datafile

        self.year = 0
        self.board_id = 0
        self.fish = 0
        self.orders_enabled: bool = True
        self.data = data
        self.datafile = datafile

    def to_board(self) -> Board:

        self.info_to_players: dict[PlayerInfo, Player] = {}
        self.info_to_provinces: dict[ProvinceInfo, Province] = {}
        self.info_to_coasts: dict[CoastInfo, Coast] = {}

        for info in self.player_infos:
            self.info_to_players[info] = Player(info, set(), set())

        for info in self.province_infos:
            unit_info = info.initial_unit
            if unit_info:
                unit = Unit(
                    unit_type=unit_info.unit_type,
                    owner=self.info_to_players[unit_info.player],
                    current_province=None,
                    coast=self.info_to_coasts.get(unit_info.coast),
                    retreat_options=None
                )
            else:
                unit = None

            province = Province(
                info=info,
                adjacent=set(),
                coasts=set(),
                core=self.info_to_players.get(info.initial_core),
                owner=self.info_to_players.get(info.initial_owner),
                unit=unit
            )

            if unit_info:
                unit.province = province
                self.info_to_players[unit_info.player].units.add(unit)

            self.info_to_provinces[info] = province
            # print(province.name())

        players: list[Player] = list(self.info_to_players.values())
        provinces: list[Province] = list(self.info_to_provinces.values())

        for province in provinces:
            info = province.info
            # set adjacent provinces
            for adjacent_info in info.adjacent:
                province.adjacent.add(self.info_to_provinces[adjacent_info])

            # set coasts
            for coast_info in info.coasts:
                coast = Coast(
                    info=coast_info,
                    adjacent_seas=set(),
                    province=province
                )
                self.info_to_coasts[coast_info] = coast

                for adjacent_info in coast_info.adjacent_seas:
                    coast.adjacent_seas.add(self.info_to_provinces[adjacent_info])

                province.coasts.add(coast)


        units: set[Unit] = set()
        for province in provinces:
            if province.unit:
                units.add(province.unit)
            if province.owner and province.info.has_supply_center:
                province.owner.centers.add(province)


        return Board(players, provinces, units, phase.initial(), self.data, self.datafile)