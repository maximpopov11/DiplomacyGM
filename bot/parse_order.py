import logging
from lark import Lark, Transformer, UnexpectedEOF
from lark.exceptions import VisitError

from bot.utils import get_unit_type, get_keywords, _manage_coast_signature
from diplomacy.persistence import order, phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, Location, Coast, ProvinceType
from diplomacy.persistence.unit import Unit, UnitType

logger = logging.getLogger(__name__)

def normalize_location(unit_type: UnitType, location: Location):
    if unit_type == UnitType.FLEET:
        if isinstance(location, Province):
            if len(location.coasts) > 1:
                raise ValueError(f"You cannot order a fleet to {location} without specifying the coast to go to")
            if len(location.coasts) == 1:
                return location.coast()
        return location
    else:
        if isinstance(location, Coast):
            return location.province
        return location


class TreeToOrder(Transformer):
    def set_state(self, board: Board, player_restriction: Player | None):
        self.board = board
        self.player_restriction = player_restriction
        
    def province(self, s) -> Location:
        name = " ".join(s[::2]).replace("_", " ").strip()
        name = _manage_coast_signature(name)
        return self.board.get_location(name)

    # used for supports, specifically FoW
    def l_unit(self, s) -> Location:
        # ignore the fleet/army signifier, if exists
        loc = s[-1]
        if loc is not None and not self.board.fow:
            unit = loc.get_unit()
            if unit is None:
                raise ValueError(f"No unit in {s[-1]}")
            if not isinstance(unit, Unit):
                raise Exception(f"Didn't get a unit or None from get_unit(), please report this")

        return loc

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

    def hold_order(self, s):
        return s[0], order.Hold()

    def core_order(self, s):
        return s[0], order.Core()
    
    def build_unit(self, s):
        if isinstance(s[2], Location):
            location = s[2]
            unit_type = s[3]
        elif isinstance(s[3], Location):
            location = s[3]
            unit_type = s[2]
        
        if isinstance(location, Coast):
            province = location.province
        else:
            province = location

        unit_type = get_unit_type(unit_type)

        location = normalize_location(unit_type, location)

        return location, province.owner, order.Build(location, unit_type)
    
    def disband_unit(self, s):
        if isinstance(s[0], Unit):
            u = s[0]
        else:
            u = s[2]
        return u.location(), u.player, order.Disband(u.location())
    
    def build(self, s):
        build_order = s[0]
        if self.player_restriction is not None and self.player_restriction != build_order[1]:
            raise Exception(f"Cannot issue order for {build_order[0].name} as you do not control it")
        remove_player_order_for_location(self.board, build_order[1], build_order[0])
        build_order[1].build_orders.add(build_order[2])
        return build_order[0]


    # format for all of these is (unit, order)
    def l_hold_order(self, s):
        return s[0], order.Hold()
    
    def l_move_order(self, s):
        # normalize position for non fow
        if not self.board.fow:
            unit_type = s[0].get_unit().unit_type
            loc = normalize_location(unit_type, s[-1])
        else:
            loc = s[-1]

        return s[0], order.Move(loc)

    def move_order(self, s):
        loc = normalize_location(s[0].unit_type, s[-1])

        return s[0], order.Move(loc)

    def convoy_order(self, s):
        return s[0], order.ConvoyTransport(s[-1][0], s[-1][1].destination)

    def support_order(self, s):
        if isinstance(s[-1], Location):
            loc = s[-1]
            unit_order = order.Hold()
        else:
            loc = s[-1][0]
            unit_order = s[-1][1]

        if isinstance(unit_order, order.Move):
            return s[0], order.Support(loc, unit_order.destination)
        elif isinstance(unit_order, order.Hold):
            return s[0], order.Support(loc, loc)
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

movement_parser = Lark(ebnf, start="order", parser="earley")
retreats_parser = Lark(ebnf, start="retreat", parser="earley")
builds_parser   = Lark(ebnf, start="build", parser="earley")

def parse_order(message: str, player_restriction: Player | None, board: Board) -> str:
    ordertext = message.split(maxsplit=1)
    if len(ordertext) == 1:
        return "For information about entering orders, please use the [player guide](https://docs.google.com/document/d/1SNZgzDViPB-7M27dTF0SdmlVuu_KYlqqzX0FQ4tWc2M/edit#heading=h.7u3tx93dufet) for examples and syntax."
    orderlist = ordertext[1].strip().splitlines()
    orderoutput = []
    errors = []
    if phase.is_builds(board.phase):
        generator.set_state(board, player_restriction)
        for order in orderlist:
            try:
                cmd = builds_parser.parse(order.lower())
                generator.transform(cmd)
                orderoutput.append(f"\u001b[0;32m{order}")
            except VisitError as e:
                logger.info(e)
                orderoutput.append(f"\u001b[0;31m{order}")
                errors.append(f"`{order}`: {str(e).splitlines()[-1]}")
            except UnexpectedEOF as e:
                logger.info(e)
                orderoutput.append(f"\u001b[0;31m{order}")
                errors.append(f"`{order}`: Please fix this order and try again")
        database = get_connection()
        database.save_build_orders_for_players(board, player_restriction)
    elif phase.is_moves(board.phase) or phase.is_retreats(board.phase):
        if phase.is_moves(board.phase):
            parser = movement_parser
        else:
            parser = retreats_parser

        generator.set_state(board, player_restriction)
        movement = []
        for order in orderlist:
            try:
                logger.info(order)
                cmd = parser.parse(order.lower())
                movement.append(generator.transform(cmd))
                orderoutput.append(f"\u001b[0;32m{order}")
            except VisitError as e:
                logger.info(e)
                orderoutput.append(f"\u001b[0;31m{order}")
                errors.append(f"`{order}`: {str(e).splitlines()[-1]}")
            except UnexpectedEOF as e:
                logger.info(e)
                orderoutput.append(f"\u001b[0;31m{order}")
                errors.append(f"`{order}`: Please fix this order and try again")

        database = get_connection()
        database.save_order_for_units(board, movement)
    else:
        return "The game is in an unknown phase. Something has gone very wrong with the bot. Please report this to a gm"
        
    output = "```ansi\n" + "\n".join(orderoutput) + "\n```"
    if errors:
        output += "\n" + "\n".join(errors)
    else:
        output += "\n" + "Orders validated successfully."
    return output


def parse_remove_order(message: str, player_restriction: Player | None, board: Board) -> str:
    invalid: list[tuple[str, Exception]] = []
    commands = str.splitlines(message)
    updated_units: set[Unit] = set()
    provinces_with_removed_builds: set[str] = set()
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

    if phase.is_builds(board.phase):
        # remove build order
        player = province.owner
        if player_restriction is not None and player != player_restriction:
            raise PermissionError(
                f"{player_restriction.name} does not control the unit in {location} which belongs to {player.name}"
            )

        remove_player_order_for_location(board, player, province)

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


def remove_player_order_for_location(board: Board, player: Player, location: Location) -> bool:
    base_province = location.as_province()
    for player_order in player.build_orders:
        if player_order.location.as_province() == base_province:
            player.build_orders.remove(player_order)
            database = get_connection()
            database.execute_arbitrary_sql(
                "DELETE FROM builds WHERE board_id=? and phase=? and location=?",
                (board.board_id, board.get_phase_and_year_string(), player_order.location.name),
            )
            return True
    return False
