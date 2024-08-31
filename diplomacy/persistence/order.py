from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence.phase import is_moves_phase, is_retreats_phase, is_adjustments_phase
from diplomacy.persistence.province import Province, Location, Coast

if TYPE_CHECKING:
    from diplomacy.persistence.board import Board
    from diplomacy.persistence.manager import Manager
    from diplomacy.persistence.player import Player
    from diplomacy.persistence.unit import Unit, UnitType


class Order:
    """Order is a player's game state API."""

    def __init__(self):
        pass


# moves, holds, etc.
class UnitOrder(Order):
    """Unit orders are orders that units execute themselves."""

    def __init__(self):
        super().__init__()


class ComplexOrder(UnitOrder):
    """Complex orders are orders that operate on other orders (supports and convoys)."""

    def __init__(self, source: Unit):
        super().__init__()
        self.source: Unit = source


class Hold(UnitOrder):
    def __init__(self):
        super().__init__()


class Core(UnitOrder):
    def __init__(self):
        super().__init__()


class Move(UnitOrder):
    def __init__(self, destination: Location):
        super().__init__()
        self.destination: Location = destination


class ConvoyMove(UnitOrder):
    def __init__(self, destination: Location):
        super().__init__()
        self.destination: Location = destination


class ConvoyTransport(ComplexOrder):
    def __init__(self, source: Unit, destination: Location):
        super().__init__(source)
        self.destination: Location = destination


class Support(ComplexOrder):
    def __init__(self, source: Unit, destination: Location):
        super().__init__(source)
        self.destination: Location = destination


class RetreatMove(UnitOrder):
    def __init__(self, destination: Location):
        super().__init__()
        self.destination: Location = destination


class RetreatDisband(UnitOrder):
    def __init__(self):
        super().__init__()


class PlayerOrder(Order):
    """Player orders are orders that belong to a player rather than a unit e.g. builds."""

    def __init__(self, location: Location):
        super().__init__()
        self.location: Location = location


class Build(PlayerOrder):
    """Builds are player orders because the unit does not yet exist."""

    # TODO: (ALPHA) what if a player wants to change their build order? need to be able to remove build/disband orders
    def __init__(self, location: Location, unit_type: UnitType):
        super().__init__(location)
        self.unit_type: UnitType = unit_type


class Disband(PlayerOrder):
    """Disbands are player order because builds are."""

    def __init__(self, location: Location):
        super().__init__(location)


def parse(message: str, player_restriction: Player | None, manager: Manager, server_id: int) -> str:
    board = manager.get_board(server_id)

    invalid: list[tuple[str, Exception]] = []
    orders = str.splitlines(message)
    for order in orders:
        try:
            _parse_order(order, player_restriction, board)
        except Exception as error:
            invalid.append((order, error))

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
north_coast = "north coast"
south_coast = "south coast"
east_coast = "east coast"
west_coast = "west coast"

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
    north_coast: ["nc", "north coast"],
    south_coast: ["sc", "south coast"],
    east_coast: ["ec", "east coast"],
    west_coast: ["wc", "west coast"],
}


def _parse_order(order: str, player_restriction: Player, board: Board):
    order = order.lower()
    parsed_locations = _parse_locations(order, board)
    unit = _get_unit(parsed_locations[0])
    if not unit:
        raise RuntimeError(f"There is no unit in {parsed_locations[0].name}.")

    player = unit.player
    if player_restriction is not None and player != player_restriction:
        raise PermissionError(
            f"You, {player_restriction.name}, do not have permissions to order the unit in {parsed_locations[0].name} "
            f"which belongs to {player.name}"
        )

    if "via" in order and "convoy" in order:
        return ConvoyMove(parsed_locations[1])

    if is_moves_phase(board.phase):
        for keyword in hold:
            if keyword in order:
                unit.order = Hold()
                return

        for keyword in core:
            if keyword in order:
                unit.order = Core()
                return

        for keyword in move:
            if keyword in order:
                unit.order = Move(parsed_locations[1])
                return

        for keyword in support:
            if keyword in order:
                unit.order = Support(_get_unit(parsed_locations[1]), parsed_locations[2])
                return

        for keyword in convoy:
            if keyword in order:
                unit.order = ConvoyTransport(_get_unit(parsed_locations[1]), parsed_locations[2])
                return
    elif is_retreats_phase(board.phase):
        for keyword in retreat_move:
            if keyword in order:
                unit.order = RetreatMove(parsed_locations[1])
                return

        for keyword in retreat_disband:
            if keyword in order:
                unit.order = RetreatDisband()
                return
    elif is_adjustments_phase(board.phase):
        for keyword in build:
            if keyword in order:
                player.adjustment_orders.add(Build(parsed_locations[0], _get_unit_type(order)))
                return

        for keyword in disband:
            if keyword in order:
                player.adjustment_orders.add(Disband(parsed_locations[0]))
                return
    else:
        raise ValueError(f"Internal error: invalid phase: {board.phase.name}")

    raise ValueError(f"No keywords found that are valid in {board.phase.name}.")


# TODO: (BETA) people will misspell provinces, use a library to find the near hits
def _parse_locations(order: str, board: Board) -> list[Location]:
    locations: list[Location] = []

    # province names are sometimes multiple words e.g. "New York" so we need to check all word-unit substrings
    words = order.split(" ")
    candidate_names = _get_candidate_names(words)
    for name in candidate_names:
        province, coast = board.get_location(name)
        if coast:
            locations.append(coast)
        elif province:
            locations.append(province)

    return locations


# TODO: (ALPHA) this does not find multi-word coast "South Coast" will not be found
# TODO: (ALPHA) this needs to be tested by something like a "F New York NC - New York South Coast", can copy and dummy
def _get_candidate_names(words: list[str]) -> list[str]:
    """Finds all substrings build from words between arbitrary indices i and j. Also includes coast translations."""
    names = []
    for i in range(len(words)):
        for j in range(i, len(words)):
            name = words[i]
            for k in range(i + 1, j):
                word = words[k]
                name += " " + word

                # if our last word in our candidate name might be a coast, input that as well
                coast = _get_coast_signature(word)
                if k == j and coast:
                    names.append(word + " " + coast)
    return names


def _get_coast_signature(string: str) -> str | None:
    if string in order_dict[north_coast]:
        return "nc"
    elif string in order_dict[south_coast]:
        return "sc"
    elif string in order_dict[east_coast]:
        return "ec"
    elif string in order_dict[west_coast]:
        return "wc"
    else:
        return None


def _get_unit(location: Location) -> Unit | None:
    if isinstance(location, Province):
        return location.unit
    elif isinstance(location, Coast):
        return location.province.unit
    else:
        raise RuntimeError(f"Location is neither a province nor a coast: {location.__class__}")


def _get_unit_type(order: str) -> UnitType:
    for word in order:
        if word in order_dict[army]:
            return UnitType.ARMY
        if word in order_dict[fleet]:
            return UnitType.FLEET

    raise ValueError(f"Unit type not found")
