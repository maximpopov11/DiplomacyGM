from bot.utils import get_unit_type, get_keywords, _manage_coast_signature
from diplomacy.persistence import order
from diplomacy.persistence.board import Board
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.phase import is_moves_phase, is_retreats_phase, is_builds_phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import Unit
from lark import Lark, Transformer


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
    _move: ["-", "->", ">", "to", "m", "move", "moves", "into"],
    _convoy_move: [
        "c-",
        "c->",
        "c>",
        "cm",
        "convoy -",
        "convoy ->",
        "convoy >",
        "convoy to",
        "convoy m",
        "convoy move",
        "convoy moves",
        "convoy into",
    ],
    _support: ["s", "support", "supports"],
    _convoy: ["c", "convoy", "convoys"],
    _core: ["core", "cores"],
    _retreat_move: ["-", "->", "to", "m", "move", "moves", "r", "retreat", "retreats"],
    _retreat_disband: ["d", "disband", "disbands", "boom", "explodes", "dies"],
    _build: ["b", "build", "place"],
    _disband: ["d", "disband", "disbands", "drop", "drops", "remove"],
}


class TreeToOrder(Transformer):
    def set_state(self, board: Board, player_restriction: Player | None):
        self.board = board
        self.player_restriction = player_restriction

    def movement_phase(self, statements):
        return set([x for x in statements if isinstance(x, Unit)])

    def retreat_phase(self, statements):
        return set([x for x in statements if x != None])

    def province(self, s):
        name = " ".join(s).replace("_", " ").strip()
        name = _manage_coast_signature(name)
        return self.board.get_location(name)

    def unit(self, s) -> Unit:
        # ignore the fleet/army signifier, if exists
        unit = s[-1].get_unit()
        if self.player_restriction is not None and unit.player != self.player_restriction:
            raise PermissionError(
                f"{self.player_restriction.name} does not control the unit in {unit.province.name}, it belongs to {unit.player.name}"
            )
        return unit

    # format for all of these is (unit, order)

    def hold_order(self, s):
        return s[0], order.Hold()

    def core_order(self, s):
        return s[0], order.Core()

    def move_order(self, s):
        return s[0], order.Move(s[-1])

    def convoy_move_order(self, s):
        return s[0], order.ConvoyMove(s[-1].destination)

    def convoy_order(self, s):
        return s[0], order.ConvoyTransport(s[-1][0], s[-1][1])

    def support_order(self, s):
        if isinstance(s[-1][1], order.Move):
            return s[0], order.Support(s[-1][0], s[-1][1].destination)
        elif isinstance(s[-1][1], order.Hold):
            return s[0], order.Support(s[-1][0], s[-1][1].get_location())

    def retreat_order(self, s):
        return s[0], order.RetreatMove(s[-1])

    def disband_order(self, s):
        return s[0], order.RetreatDisband(s[-1])

    def order(self, order):
        if len(order) == 0:
            # this line is '.order'
            return None
        (command,) = order
        unit, order = command
        unit.order = order
        return unit


generator = TreeToOrder()


with open("bot/orders.ebnf", "r") as f:
    ebnf = f.read()

movement_parser = Lark(ebnf, start="movement_phase", parser="earley")
retreats_parser = Lark(ebnf, start="retreat_phase", parser="earley")


# TODO: (!) illegal orders (wrong phase or doesn't work) should get caught when ordered, not on adjudication
def parse_order(message: str, player_restriction: Player | None, board: Board) -> str:
    invalid: list[tuple[str, Exception]] = []
    if is_builds_phase(board.phase):
        for command in str.splitlines(message):
            try:
                _parse_player_order(get_keywords(command), player_restriction, board)
            except Exception as error:
                invalid.append((command, error))
        if invalid:
            response = "The following orders were invalid:"
            for command in invalid:
                response += f"\n{command[0]} with error: {command[1]}"
        else:
            response = "Orders validated successfully."

        return response
    elif is_moves_phase(board.phase) or is_retreats_phase(board.phase):
        if is_moves_phase(board.phase):
            parser = movement_parser
        else:
            parser = retreats_parser

        generator.set_state(board, player_restriction)
        cmd = parser.parse(message.lower())
        movement = generator.transform(cmd)

        database = get_connection()
        database.save_order_for_units(board, movement)

        return "Orders validated successfully"
    else:
        return "The game is in an unknown phase. Something has gone very wrong with the bot. Please report this to a gm"


def parse_remove_order(message: str, player_restriction: Player | None, board: Board) -> str:
    invalid: list[tuple[str, Exception]] = []
    commands = str.splitlines(message)
    updated_units: set[Unit] = set()
    for command in commands:
        if command.strip() == ".remove_order":
            continue
        try:
            unit = _parse_remove_order(command, player_restriction, board)
            if unit is not None:
                updated_units.add(unit)
        except Exception as error:
            invalid.append((command, error))

    database = get_connection()
    database.save_order_for_units(board, list(updated_units))

    if invalid:
        response = "The following order removals were invalid:"
        for command in invalid:
            response += f"\n{command[0]} with error: {command[1]}"
    else:
        response = "Orders removed successfully."

    return response


def _parse_remove_order(command: str, player_restriction: Player, board: Board) -> Unit | None:
    command = command.lower()
    keywords: list[str] = get_keywords(command)
    location = keywords[0]
    province, _ = board.get_province_and_coast(location)

    # remove unit order
    unit = province.get_unit()
    if is_builds_phase(board.phase):
        # remove build order
        player = province.owner
        if player_restriction is not None and player != player_restriction:
            raise PermissionError(
                f"{player_restriction.name} does not control the unit in {location} which belongs to {player.name}"
            )

        remove_order = None
        for build_order in player.build_orders:
            if build_order.location == province:
                remove_order = build_order
                break
        if remove_order:
            player.build_orders.remove(remove_order)
        return None
    else:
        # remove unit's order
        # assert that the command user is authorized to order this unit
        player = unit.player
        if player_restriction is not None and player != player_restriction:
            raise PermissionError(
                f"{player_restriction.name} does not control the unit in {location} which belongs to {player.name}"
            )
        unit.order = None
        return unit


def _parse_player_order(keywords: list[str], player_restriction: Player, board: Board) -> None:
    command = keywords[0]
    location = board.get_location(keywords[1])

    if location.get_owner() != player_restriction:
        raise PermissionError(f"{player_restriction} does not control {location.name}")

    if command in _order_dict[_build]:
        unit_type = get_unit_type(keywords[2])
        player_restriction.build_orders.add(order.Build(location, unit_type))
        return

    if command in _order_dict[_disband]:
        player_restriction.build_orders.add(order.Disband(location))
        return

    raise RuntimeError("Build could not be parsed")
