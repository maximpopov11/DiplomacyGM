from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence.phase import is_moves_phase, is_retreats_phase, is_adjustments_phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, Location, Coast
from diplomacy.persistence.unit import Unit, UnitType

if TYPE_CHECKING:
    from diplomacy.persistence.board import Board
    from diplomacy.persistence.manager import Manager


class Order:
    def __init__(self, player: Player):
        self.player = player


class UnitOrder(Order):
    def __init__(self, unit: Unit):
        super().__init__(unit.player)
        self.unit: Unit = unit


class ComplexOrder(UnitOrder):
    """Complex orders are orders that operate on other orders (supports and convoys)."""

    def __init__(self, unit: Unit, source: Unit):
        super().__init__(unit)
        self.source: Unit = source


class Hold(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Core(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Move(UnitOrder):
    def __init__(self, unit: Unit, destination: Location):
        super().__init__(unit)
        self.destination: Location = destination


class ConvoyMove(UnitOrder):
    def __init__(self, unit: Unit, destination: Location):
        super().__init__(unit)
        self.destination: Location = destination


class ConvoyTransport(ComplexOrder):
    def __init__(self, unit: Unit, source: Unit, destination: Location):
        assert unit.unit_type == UnitType.FLEET, "Convoying unit must be a fleet."
        assert source.unit_type == UnitType.ARMY, "Convoyed unit must be an army."
        super().__init__(unit, source)
        self.destination: Location = destination


class Support(ComplexOrder):
    def __init__(self, unit: Unit, source: Unit, destination: Location):
        super().__init__(unit, source)
        self.destination: Location = destination


class RetreatMove(UnitOrder):
    def __init__(self, unit: Unit, destination: Location):
        super().__init__(unit)
        self.destination: Location = destination


class RetreatDisband(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Build(Order):
    def __init__(self, province: Location, unit_type: UnitType):
        super().__init__(province.owner)
        self.province: Location = province
        self.unit_type: UnitType = unit_type


class Disband(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


def parse(message: str, player_restriction: Player | None, manager: Manager, server_id: int) -> str:
    board = manager.get_board(server_id)

    valid: list[Order] = []
    invalid: list[tuple[str, Exception]] = []
    orders = str.splitlines(message)
    for order in orders:
        try:
            valid.append(_parse_order(order, player_restriction, board))
        except Exception as error:
            invalid.append((order, error))
    manager.add_orders(server_id, valid)

    if invalid:
        response = "The following orders were invalid:"
        for order in invalid:
            response += f"\n{order[0]} with error: {order[1]}"
    else:
        response = "Orders validated successfully."

    return response


hold = "hold"
move = "move"
support = "support"
convoy = "convoy"
retreat_move = "retreat move"
retreat_disband = "retreat disband"
build = "build"
disband = "disband"
core = "core"
army = "army"
fleet = "fleet"

order_dict = {
    hold: ["h", "hold", "holds"],
    move: ["-", "->", "to", "m", "move", "moves"],
    support: ["s", "support", "supports"],
    convoy: ["c", "convoy", "convoys"],
    core: ["core", "cores"],
    retreat_move: ["-", "->", "to", "m", "move", "moves", "r", "retreat", "retreats"],
    retreat_disband: ["d", "disband", "disbands", "boom", "explodes", "dies"],
    build: ["b", "build", "place"],
    disband: ["d", "disband", "disbands", "drop", "drops", "remove"],
    army: ["a", "army", "cannon"],
    fleet: ["f", "fleet", "boat", "ship"],
}


def _parse_order(order: str, player_restriction: Player, board: Board) -> Order:
    order = order.lower()

    parsed_locations = _parse_locations(order, board.provinces)
    location0 = parsed_locations[0]
    location1 = parsed_locations[1]
    location2 = parsed_locations[2]

    unit1 = _get_unit(location0)
    if not unit1:
        raise RuntimeError(f"There is no unit in {location0.name}.")
    unit2 = _get_unit(location1)

    player = unit1.player
    if player_restriction is not None and player != player_restriction:
        raise PermissionError(
            f"You, {player_restriction.name}, do not have permissions to order the unit in {location0.name} which "
            f"belongs to {player.name}"
        )

    if "via" in order and "convoy" in order:
        return ConvoyMove(unit1, location1)

    if is_moves_phase(board.phase):
        for keyword in hold:
            if keyword in order:
                return Hold(unit1)

        for keyword in core:
            if keyword in order:
                return Core(unit1)

        for keyword in move:
            if keyword in order:
                return Move(unit1, location1)

        for keyword in support:
            if keyword in order:
                return Support(unit1, unit2, location2)

        for keyword in convoy:
            if keyword in order:
                return ConvoyTransport(unit1, unit2, location2)
    elif is_retreats_phase(board.phase):
        for keyword in retreat_move:
            if keyword in order:
                return RetreatMove(unit1, location1)

        for keyword in retreat_disband:
            if keyword in order:
                return RetreatDisband(unit1)
    elif is_adjustments_phase(board.phase):
        for keyword in build:
            if keyword in order:
                unit_type = None
                for word in order:
                    if word in order_dict[army]:
                        unit_type = UnitType.ARMY
                        break
                    if word in order_dict[fleet]:
                        unit_type = UnitType.FLEET
                        break
                if not unit_type:
                    raise ValueError(f"Unit type not found.")
                return Build(location1, unit_type)

        for keyword in disband:
            if keyword in order:
                return Disband(unit1)
    else:
        raise ValueError(f"Internal error: invalid phase: {board.phase.name}")

    raise ValueError(f"No keywords found that are valid in {board.phase.name}.")


# TODO: (BETA) people will misspell provinces, use a library to find the near hits
def _parse_locations(order: str, all_provinces: set[Province]) -> list[Location]:
    name_to_province = {province.name.lower(): province for province in all_provinces}

    locations: list[Location] = []
    for word in order:
        if word in name_to_province:
            province = name_to_province[word]
            coast = _get_coast(order, province)
            if coast:
                locations.append(coast)
            else:
                locations.append(province)

    return locations


def _get_coast(order: str, province: Province) -> Coast | None:
    if "nc" in order or "north coast" in order:
        return next((coast for coast in province.coasts if coast.name == f"{province.name} nc"), None)
    elif "sc" in order or "south coast" in order:
        return next((coast for coast in province.coasts if coast.name == f"{province.name} sc"), None)
    elif "ec" in order or "east coast" in order:
        return next((coast for coast in province.coasts if coast.name == f"{province.name} ec"), None)
    elif "wc" in order or "west coast" in order:
        return next((coast for coast in province.coasts if coast.name == f"{province.name} wc"), None)
    else:
        return None


def _get_unit(location: Location) -> Unit | None:
    if isinstance(location, Province):
        return location.unit
    elif isinstance(location, Coast):
        return location.province.unit
    else:
        raise RuntimeError(f"Location is neither a province nor a coast: {location.__class__}")
