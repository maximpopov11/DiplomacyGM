from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence.phase import is_moves_phase, is_retreats_phase, is_adjustments_phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province
from diplomacy.persistence.unit import Unit, UnitType

if TYPE_CHECKING:
    from diplomacy.persistence.board import Board
    from diplomacy.persistence.manager import Manager


class Order:
    def __init__(self):
        pass


class UnitOrder(Order):
    def __init__(self, unit: Unit):
        super().__init__()
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
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination: Province = destination


class ConvoyMove(UnitOrder):
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination: Province = destination


class ConvoyTransport(ComplexOrder):
    def __init__(self, unit: Unit, source: Unit, destination: Province):
        assert unit.unit_type == UnitType.FLEET, "Convoying unit must be a fleet."
        assert source.unit_type == UnitType.ARMY, "Convoyed unit must be an army."
        super().__init__(unit, source)
        self.destination: Province = destination


class Support(ComplexOrder):
    def __init__(self, unit: Unit, source: Unit, destination: Province):
        super().__init__(unit, source)
        self.destination: Province = destination


class RetreatMove(UnitOrder):
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination: Province = destination


class RetreatDisband(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Build(Order):
    def __init__(self, province: Province, unit_type: UnitType):
        super().__init__()
        self.province: Province = province
        self.unit_type: UnitType = unit_type


class Disband(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


def parse(message: str, player_restriction: Player | None, manager: Manager, server_id: int) -> str:
    board = manager.get_board(server_id)

    valid: list[Order] = set()
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

    parsed_provinces = _parse_provinces(order, board.provinces)
    province0 = parsed_provinces[0]
    province1 = parsed_provinces[1]
    province2 = parsed_provinces[2]

    unit1 = province0.unit
    if not unit1:
        raise RuntimeError(f"There is no unit in {province0.name}.")
    unit2 = province1.unit

    player = unit1.player
    if player_restriction is not None and player != player_restriction:
        raise PermissionError(
            f"You, {player_restriction.name}, do not have permissions to order the unit in {province0.name} which "
            f"belongs to {player.name}"
        )

    if "via" in order and "convoy" in order:
        return ConvoyMove(unit1, province1)

    if is_moves_phase(board.phase):
        for keyword in hold:
            if keyword in order:
                return Hold(unit1)

        for keyword in core:
            if keyword in order:
                return Core(unit1)

        for keyword in move:
            if keyword in order:
                return Move(unit1, province1)

        for keyword in support:
            if keyword in order:
                return Support(unit1, unit2, province2)

        for keyword in convoy:
            if keyword in order:
                return ConvoyTransport(unit1, unit2, province2)
    elif is_retreats_phase(board.phase):
        for keyword in retreat_move:
            if keyword in order:
                return RetreatMove(unit1, province1)

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
                return Build(province1, unit_type)

        for keyword in disband:
            if keyword in order:
                return Disband(unit1)
    else:
        raise ValueError(f"Internal error: invalid phase: {board.phase.name}")

    raise ValueError(f"No keywords found that are valid in {board.phase.name}.")


# TODO: (ALPHA) people will misspell provinces, use a library to find the near hits
def _parse_provinces(order: str, all_provinces: set[Province]) -> list[Province]:
    name_to_province = {province.name.lower(): province for province in all_provinces}
    provinces = []
    for word in order:
        if word in name_to_province:
            provinces.append(name_to_province[word])
    return provinces
