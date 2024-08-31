from diplomacy.persistence.phase import Phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, Coast
from diplomacy.persistence.unit import Unit, UnitType


class Board:
    def __init__(
        self,
        players: set[Player],
        provinces: set[Province],
        units: set[Unit],
        phase: Phase,
    ):
        self.players: set[Player] = players
        self.provinces: set[Province] = provinces
        self.units: set[Unit] = units
        self.phase: Phase = phase

    # TODO: (BETA) make this efficient
    def get_player(self, name: str) -> Player:
        return next((player for player in self.players if player.name == name), None)

    # TODO: (BETA) make this efficient
    def get_province(self, name: str) -> Province:
        return next((province for province in self.provinces if province.name == name), None)

    def get_build_counts(self) -> list[tuple[str, int]]:
        build_counts = []
        for player in self.players:
            build_counts.append((player.name, len(player.centers) - len(player.units)))
        build_counts = sorted(build_counts, key=lambda counts: counts[1])
        return build_counts

    def get_location(self, name: str) -> tuple[Province, Coast | None]:
        # TODO: (BETA) we build this everywhere, let's just have one live on the Board on init
        name_to_province: dict[str, Province] = {}
        name_to_coast: dict[str, Coast] = {}
        for province in self.provinces:
            name_to_province[province.name] = province
            for coast in province.coasts:
                name_to_coast[coast.name] = coast

        coast = name_to_coast.get(name)
        if coast:
            return coast.province, coast
        else:
            return name_to_province[name], None

    def create_unit(
        self,
        unit_type: UnitType,
        player: Player,
        province: Province,
        coast: Coast | None,
        retreat_options: set[Province] | None,
    ) -> None:
        unit = Unit(unit_type, player, province, coast, retreat_options)
        if retreat_options:
            province.dislodged_unit = unit
        else:
            province.unit = unit
        player.units.add(unit)
        self.units.add(unit)

    def delete_all_units(self) -> None:
        for unit in self.units:
            unit.province.unit = None

        for player in self.players:
            player.units = set()

        self.units = set()
