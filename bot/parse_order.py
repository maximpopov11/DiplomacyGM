from bot.utils import get_unit_type, get_keywords
from diplomacy.persistence import order
from diplomacy.persistence.board import Board
from diplomacy.persistence.phase import is_moves_phase, is_retreats_phase, is_builds_phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import Unit

_hold = "hold"
_move = "move"
_convoy_move = "convoy move"
_support = "support"
_convoy = "convoy"
_core = "core"
_retreat_move = "retreat move"
_retreat_disband = "retreat disband"
_build = "build"
_disband = "disband"

_order_dict = {
    _hold: ["h", "hold", "holds"],
    _move: ["-", "->", "to", "m", "move", "moves"],
    _convoy_move: ["c-", "cm", "convoy -", "convoy ->", "convoy to", "convoy m", "convoy move", "convoy moves"],
    _support: ["s", "support", "supports"],
    _convoy: ["c", "convoy", "convoys"],
    _core: ["core", "cores"],
    _retreat_move: ["-", "->", "to", "m", "move", "moves", "r", "retreat", "retreats"],
    _retreat_disband: ["d", "disband", "disbands", "boom", "explodes", "dies"],
    _build: ["b", "build", "place"],
    _disband: ["d", "disband", "disbands", "drop", "drops", "remove"],
}


def parse_order(message: str, player_restriction: Player | None, board: Board) -> str:
    invalid: list[tuple[str, Exception]] = []
    commands = str.splitlines(message)
    for command in commands:
        try:
            _parse_order(command, player_restriction, board)
        except Exception as error:
            invalid.append((command, error))

    if invalid:
        response = "The following orders were invalid:"
        for command in invalid:
            response += f"\n{command[0]} with error: {command[1]}"
    else:
        response = "Orders validated successfully."

    return response


def parse_remove_order(message: str, player_restriction: Player | None, board: Board) -> str:
    invalid: list[tuple[str, Exception]] = []
    commands = str.splitlines(message)
    for command in commands:
        try:
            _parse_remove_order(command, player_restriction, board)
        except Exception as error:
            invalid.append((command, error))

    if invalid:
        response = "The following order removals were invalid:"
        for command in invalid:
            response += f"\n{command[0]} with error: {command[1]}"
    else:
        response = "Orders removed successfully."

    return response


def _parse_order(command: str, player_restriction: Player, board: Board) -> None:
    command = command.lower()
    keywords: list[str] = get_keywords(command)

    is_unit_order = is_moves_phase(board.phase) or is_retreats_phase(board.phase)
    if is_unit_order:
        if get_unit_type(keywords[0]):
            # we can ignore unit type if provided
            keywords = keywords[1:]

        # all unit orders must specify their unit
        location = board.get_location(keywords[0])
        unit = location.get_unit()
        if not unit:
            raise RuntimeError(f"There is no unit in {location.name}")
        keywords = keywords[1:]

        # assert that the command user is authorized to order this unit
        player = unit.player
        if player_restriction is not None and player != player_restriction:
            raise PermissionError(
                f"{player_restriction.name} does not control the unit in {location.name} which belongs to {player.name}"
            )

        _parse_unit_order(keywords, unit, board)
    elif is_builds_phase(board.phase):
        _parse_player_order(keywords, player_restriction, board)
    else:
        raise ValueError(f"Unknown phase: {board.phase.name}")


def _parse_remove_order(command: str, player_restriction: Player, board: Board) -> None:
    command = command.lower()
    keywords: list[str] = get_keywords(command)
    location = keywords[0]
    province, _ = board.get_province_and_coast(location)

    unit = province.get_unit()
    if not unit:
        raise RuntimeError(f"There is no unit in {location}")

    # assert that the command user is authorized to order this unit
    player = unit.player
    if player_restriction is not None and player != player_restriction:
        raise PermissionError(
            f"{player_restriction.name} does not control the unit in {location} which belongs to {player.name}"
        )

    unit.order = None


def _parse_unit_order(keywords: list[str], unit: Unit, board: Board) -> None:
    command = keywords[0]

    # no extra data orders
    if command in _order_dict[_hold]:
        unit.order = order.Hold()
        return
    if command in _order_dict[_core]:
        unit.order = order.Core()
        return
    if command in _order_dict[_retreat_disband]:
        unit.order = order.RetreatDisband()
        return

    # all remaining orders require a province next
    keywords = keywords[1:]
    location = board.get_location(keywords[0])

    if command in _order_dict[_move]:
        unit.order = order.Move(location)
        return
    if command in _order_dict[_convoy_move]:
        unit.order = order.ConvoyMove(location)
        return
    if command in _order_dict[_retreat_move]:
        unit.order = order.RetreatMove(location)
        return

    # all remaining orders require more data
    keywords = keywords[1:]

    if command in _order_dict[_support]:
        if keywords[0] in _order_dict[_hold] or keywords[0] == location:
            # support hold
            location2 = location
        else:
            # support move
            if keywords[0] in _order_dict[_move]:
                # this is irrelevant if provided, we already know this is a support move
                keywords = keywords[1:]
            location2 = board.get_location(keywords[0])

        unit.order = order.Support(location.get_unit(), location2)
        return

    if command in _order_dict[_convoy]:
        if keywords[0] in _order_dict[_move]:
            # this is irrelevant if provided
            keywords = keywords[1:]
        location2 = board.get_location(keywords[0])

        unit.order = order.ConvoyTransport(location.get_unit(), location2)
        return

    raise RuntimeError("Moves/Retreats order could not be parsed")


def _parse_player_order(keywords: list[str], player_restriction: Player, board: Board) -> None:
    command = keywords[0]
    location = board.get_location(keywords[1])

    if location.get_owner() != player_restriction:
        raise PermissionError(f"{player_restriction} does not control {location.name}")

    if command in _order_dict[_build]:
        unit_type = get_unit_type(keywords[2])
        player_restriction.adjustment_orders.add(order.Build(location, unit_type))
        return

    if command in _order_dict[_disband]:
        player_restriction.adjustment_orders.add(order.Disband(location))
        return

    raise RuntimeError("Build could not be parsed")
