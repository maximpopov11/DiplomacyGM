from lark import Lark, Transformer

from bot.utils import get_unit_type, get_keywords, _manage_coast_signature
from diplomacy.persistence import order
from diplomacy.persistence.board import Board
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.phase import is_moves_phase, is_retreats_phase, is_builds_phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province
from diplomacy.persistence.unit import Unit, UnitType

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
    _hold: ["h", "hold", "holds", "stand", "stands"],
    _move: ["-", "–", "->", "–>", ">", "to", "m", "move", "moves", "into"],
    _convoy_move: [
        "c-",
        "c–",
        "c->",
        "c–>",
        "c>",
        "cm",
        "convoy -",
        "convoy –",
        "convoy ->",
        "convoy –>",
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
    _retreat_move: ["-", "–", "->", "–>", "to", "m", "move", "moves", "r", "retreat", "retreats"],
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
        return set([x for x in statements if isinstance(x, Unit)])

    def province(self, s):
        name = " ".join(s[::2]).replace("_", " ").strip()
        name = _manage_coast_signature(name)
        return self.board.get_location(name)

    def unit(self, s) -> Unit:
        # ignore the fleet/army signifier, if exists
        unit = s[-1].get_unit()
        if unit is None:
            raise ValueError(f"No unit in {s[-1]}")
        if not isinstance(unit, Unit):
            raise Exception(f"Didn't get a unit or None from get_unit(), please report this")

        return unit

    def retreat_unit(self, s) -> Unit:
        # ignore the fleet/army signifier, if exists
        unit = s[-1].dislodged_unit
        if unit is None:
            raise ValueError(f"No dislodged unit in {s[-1]}")
        if not isinstance(unit, Unit):
            raise Exception(f"Didn't get a unit or None from get_unit(), please report this")

        return unit

    # format for all of these is (unit, order)

    def hold_order(self, s):
        return s[0], order.Hold()

    def core_order(self, s):
        return s[0], order.Core()

    def move_order(self, s):
        return s[0], order.Move(s[-1])

    def convoy_move_order(self, s):
        return s[0], order.Move(s[-1])

    def convoy_order(self, s):
        return s[0], order.ConvoyTransport(s[-1][0], s[-1][1].destination)

    def support_order(self, s):
        if isinstance(s[-1][1], order.Move):
            return s[0], order.Support(s[-1][0], s[-1][1].destination)
        elif isinstance(s[-1][1], order.Hold):
            return s[0], order.Support(s[-1][0], s[-1][0].get_location())
        else:
            raise ValueError("Unknown type of support. Something has broken in the bot. Please report this")

    def retreat_order(self, s):
        return s[0], order.RetreatMove(s[-1])

    def disband_order(self, s):
        return s[0], order.RetreatDisband()

    def order(self, order):
        (command,) = order
        unit, order = command
        if self.player_restriction is not None and unit.player != self.player_restriction:
            raise PermissionError(
                f"{self.player_restriction.name} does not control the unit in {unit.province.name}, it belongs to {unit.player.name}"
            )
        unit.order = order
        return unit

    def retreat(self, order):
        (command,) = order
        unit, order = command
        if self.player_restriction is not None and unit.player != self.player_restriction:
            raise PermissionError(
                f"{self.player_restriction.name} does not control the unit in {unit.province.name}, it belongs to {unit.player.name}"
            )
        unit.order = order
        return unit


generator = TreeToOrder()


with open("bot/orders.ebnf", "r") as f:
    ebnf = f.read()

movement_parser = Lark(ebnf, start="movement_phase", parser="earley")
retreats_parser = Lark(ebnf, start="retreat_phase", parser="earley")


def parse_order(message: str, player_restriction: Player | None, board: Board) -> str:
    invalid: list[tuple[str, Exception]] = []
    if is_builds_phase(board.phase):
        for command in str.splitlines(message):
            try:
                if command.strip() != ".order":
                    _parse_player_order(get_keywords(command.lower()), player_restriction, board)
            except Exception as error:
                invalid.append((command, error))

        database = get_connection()
        database.save_build_orders_for_players(board, player_restriction)

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
        cmd = parser.parse(message.lower() + "\n")
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
    provinces_with_removed_builds: set[Province] = set()
    for command in commands:
        if command.strip() == ".remove_order":
            continue
        try:
            removed = _parse_remove_order(command, player_restriction, board)
            if isinstance(removed, Unit):
                updated_units.add(removed)
            else:
                provinces_with_removed_builds.add(removed)
        except Exception as error:
            invalid.append((command, error))

    database = get_connection()
    database.save_order_for_units(board, list(updated_units))
    for province in provinces_with_removed_builds:
        database.execute_arbitrary_sql(
            "DELETE FROM builds WHERE board_id=? and phase=? and location=?",
            (board.board_id, board.get_phase_and_year_string(), province),
        )

    if invalid:
        response = "The following order removals were invalid:"
        for command in invalid:
            response += f"\n{command[0]} with error: {command[1]}"
    else:
        response = "Orders removed successfully."

    return response


def _parse_remove_order(command: str, player_restriction: Player, board: Board) -> Unit | str:
    command = command.lower()
    keywords: list[str] = get_keywords(command)
    if keywords[0] == ".remove order":
        keywords = keywords[1:]
    location = keywords[0]
    province, coast = board.get_province_and_coast(location)

    if is_builds_phase(board.phase):
        # remove build order
        player = province.owner
        if player_restriction is not None and player != player_restriction:
            raise PermissionError(
                f"{player_restriction.name} does not control the unit in {location} which belongs to {player.name}"
            )

        for build_order in player.build_orders:
            if build_order.location == province:
                player.build_orders.remove(build_order)
                break

        if coast is None:
            if province.coasts:
                return str(province.coast())
            return province.name
        else:
            return province.name + " " + coast.name
    else:
        # remove unit's order
        # assert that the command user is authorized to order this unit
        unit = province.get_unit()
        if unit is not None:
            player = unit.player
            if player_restriction is None or player == player_restriction:
                unit.order = None
            return unit
        unit = province.dislodged_unit
        if unit is not None:
            player = unit.player
            if player_restriction is None or player == player_restriction:
                unit.order = None
            return unit
        raise Exception(f"You control neither the unit nor dislodged unit in province {province.name}")


def _parse_player_order(keywords: list[str], player_restriction: Player | None, board: Board) -> Player:
    if keywords[0] == ".order":
        keywords = keywords[1:]
    command = keywords[0]
    try:
        location = board.get_location(keywords[1])
    except KeyError as original_error:
        keywords[1], keywords[2] = keywords[2], keywords[1]
        try:
            location = board.get_location(keywords[1])
        except KeyError:
            raise original_error

    if player_restriction is not None and location.get_owner() != player_restriction:
        raise PermissionError(f"{player_restriction} does not control {location.name}")

    player = player_restriction
    if player is None:
        player = location.get_owner()
    if player is None:
        raise ValueError(f"{location.name} is not owned by anyone")

    if command in _order_dict[_build]:
        unit_type = get_unit_type(keywords[2])
        if unit_type == UnitType.FLEET:
            if isinstance(location, Province):
                location = location.coast()
        player_order = order.Build(location, unit_type)
        # This is jank. Probably bad practice? PlayerOrder class implements __eq__ to only check location
        # So basically we have to remove the other equivalent one if it's in there and add ourselves
        if player_order in player.build_orders:
            player.build_orders.remove(player_order)
        player.build_orders.add(player_order)
        return player

    if command in _order_dict[_disband]:
        player_order = order.Disband(location)
        if player_order in player.build_orders:
            player.build_orders.remove(player_order)
        player.build_orders.add(player_order)
        return player

    raise RuntimeError("Build could not be parsed")
