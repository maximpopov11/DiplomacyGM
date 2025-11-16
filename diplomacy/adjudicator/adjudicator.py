import abc
import collections
import logging

from diplomacy.adjudicator.defs import (
    ResolutionState,
    Resolution,
    AdjudicableOrder,
    OrderType,
)
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.order import (
    Order,
    NMR,
    Hold,
    Move,
    Core,
    ConvoyMove,
    RetreatMove,
    ConvoyTransport,
    Support,
    RetreatDisband,
    ComplexOrder,
    Build,
    Disband,
    Disown,
    Vassal,
    Liege,
    Defect,
    DualMonarchy,
    RebellionMarker
)

from diplomacy.persistence.player import Player, PlayerClass
from diplomacy.persistence.province import Location, Coast, Province, ProvinceType, get_adjacent_provinces
from diplomacy.persistence.unit import UnitType, Unit
from diplomacy.persistence.db import database

logger = logging.getLogger(__name__)




def convoy_is_possible(start: Province, end: Province, check_fleet_orders=False) -> bool:
    """
    Breadth-first search to figure out if start -> end is possible passing over fleets

    :param start: Start province
    :param end: End province
    :param check_fleet_orders: if True, check that the fleets along the way are actually convoying the unit
    :return: True if there are fleets connecting start -> end
    """
    visited: set[str] = set()
    to_visit = collections.deque()
    to_visit.append(start)
    while 0 < len(to_visit):
        current = to_visit.popleft()

        if current.name in visited:
            continue
        visited.add(current.name)

        for adjacent_province in current.adjacent:
            if adjacent_province == end:
                return True
            if adjacent_province.type != ProvinceType.SEA:
                continue
            if adjacent_province.unit is None or adjacent_province.unit.unit_type != UnitType.FLEET:
                continue
            if check_fleet_orders:
                fleet_order = adjacent_province.unit.order
                if fleet_order is None:
                    continue
                if not isinstance(fleet_order, ConvoyTransport):
                    continue
                if fleet_order.source is not start or fleet_order.destination is not end:
                    continue
            to_visit.append(adjacent_province)

    return False


def order_is_valid(location: Location, order: Order, strict_convoys_supports=False, strict_coast_movement=True) -> tuple[bool, str | None]:
    """
    Checks if order from given location is valid for configured board

    :param location: Province or Coast the order originates from
    :param order: Order to check
    :param strict_convoys_supports: Defaults False. Validates only if supported order was also ordered,
                                    or convoyed unit was convoyed correctly
    :param strict_coast_movement: Defaults True. Checks movement regarding coasts, should be false when checking 
                                    for support holds.
    :return: tuple(result, reason)
        - bool result is True if the order is valid, False otherwise
        - str reason is arbitrary if the order is valid, provides reasoning if invalid
    """
    if order is None:
        return False, "Order is missing"

    if isinstance(order, Support) or isinstance(order, ConvoyTransport):
        source = order.source
        source_unit = source.get_unit()

        if source_unit == None:
            return False, f"No unit for supporting / convoying at {source}"

        order.source = source_unit.location()

        # Quick FOW fix for supports
        if source_unit.unit_type == UnitType.FLEET and isinstance(order.destination, Province):
            if len(order.destination.coasts) == 1:
                order.destination = order.destination.coast()
        if source_unit.unit_type == UnitType.ARMY and isinstance(order.destination, Coast):
                order.destination = order.destination.province


    unit = location.as_province().unit
    if unit is None:
        return False, f"There is no unit in {location.name}"

    if isinstance(order, Hold) or isinstance(order, RetreatDisband) or isinstance(order, NMR):
        return True, None
    elif isinstance(order, Core):
        if not location.as_province().has_supply_center:
            return False, f"{location.name} does not have a supply center to core"
        if location.get_owner() != unit.player:
            return False, "Units can only core in owned supply centers"
        return True, None
    elif isinstance(order, Move) or isinstance(order, RetreatMove):
        destination_province = order.destination.as_province()
        if unit.unit_type == UnitType.ARMY:
            if destination_province not in get_adjacent_provinces(location):
                return False, f"{location.name} does not border {order.destination.name}"
            if destination_province.type == ProvinceType.SEA:
                return False, "Armies cannot move to sea provinces"
        elif unit.unit_type == UnitType.FLEET:
            check = order.destination.as_province() in get_adjacent_provinces(location)

            # FIXME currently adjacencies for coasts don't work properly, and allow for supporting from different coasts when necessary
            # when this is fixed, please uncomment out tests test_6_b_3_variant, test_6_d_29, test_6_d_30 as they fail currently
            source = location
            destination = order.destination
            # supports don't need to be strict
            if strict_coast_movement:
                if isinstance(source, Coast) and isinstance(destination, Coast):
                    # coast to coast
                    check = destination in source.adjacent_coasts
                elif isinstance(source, Coast) and isinstance(destination, Province):
                    # coast to sea / island
                    if destination.type == ProvinceType.LAND:
                        return False, f"Fleet destination should be a coast"
                    check = destination in source.adjacent_seas
                elif isinstance(source, Province) and isinstance(destination, Coast):
                    # sea / island to coast
                    if source.type == ProvinceType.LAND:
                        return False, f"Fleet source {source} should be a coast"
                    check = source in destination.adjacent_seas
                elif isinstance(source, Province) and isinstance(destination, Province):
                    # sea / island to sea / island
                    check = source in destination.adjacent

            if not check:
                return False, f"{location.name} does not border {order.destination.name}"
        else:
            raise ValueError("Unknown type of unit. Something has broken in the bot. Please report this")

        if isinstance(order, RetreatMove) and destination_province.unit is not None:
            return False, "Cannot retreat to occupied provinces"
        return True, None
    elif isinstance(order, ConvoyMove):
        if unit.unit_type != UnitType.ARMY:
            return False, "Only armies can be convoyed"
        destination_province = order.destination.as_province()
        if destination_province.type == ProvinceType.SEA:
            return False, "Cannot convoy to a sea space"
        if destination_province == unit.location():
            return False, "Cannot convoy army to its previous space"
        return (
            convoy_is_possible(
                location.as_province(),
                destination_province,
                check_fleet_orders=strict_convoys_supports,
            ),
            f"No valid convoy path from {location.name} to {order.destination.name}",
        )
    elif isinstance(order, ConvoyTransport):
        if unit.unit_type != UnitType.FLEET:
            return False, "Only fleets can convoy"
        if strict_convoys_supports:
            corresponding_order_is_move = isinstance(order.source.get_unit().order, Move) or isinstance(
                order.source.get_unit().order, ConvoyMove
            )
            if not corresponding_order_is_move or order.source.get_unit().order.destination.as_province() != order.destination.as_province():
                return False, f"Convoyed unit {order.source} did not make corresponding order"
        valid_move, reason = order_is_valid(
            order.source.as_province(), ConvoyMove(order.destination), strict_convoys_supports
        )
        if not valid_move:
            return valid_move, reason
        # Check we are actually part of the convoy chain
        destination_province = order.destination.as_province()
        if not convoy_is_possible(
            order.source.as_province(), destination_province, check_fleet_orders=strict_convoys_supports
        ):
            return False, f"No valid convoy path from {order.source.name} to {location.name}"
        return True, None
    elif isinstance(order, Support):
        if isinstance(order.source.get_unit().order, Core) and order_is_valid(order.source.as_province(), Core):
            return False, f"Cannot support a unit that is coring"

        move_valid, _ = order_is_valid(location, Move(order.destination), strict_convoys_supports, False)
        if not move_valid:
            return False, f"Cannot support somewhere you can't move to"

        is_support_hold = order.source.as_province() == order.destination.as_province()
        source_to_destination_valid = (
            is_support_hold
            or order_is_valid(order.source, Move(order.destination), strict_convoys_supports)[0]
            or order_is_valid(order.source, ConvoyMove(order.destination), strict_convoys_supports)[0]
        )

        if not source_to_destination_valid:
            return False, "Supported unit can't reach destination"

        if strict_convoys_supports:
            corresponding_order_is_move = isinstance(order.source.get_unit().order, Move) or isinstance(
                order.source.get_unit().order, ConvoyMove
            )
            # if move is invalid then it doesn't go through
            if (
                is_support_hold and corresponding_order_is_move
            ) or (
                not is_support_hold and (not corresponding_order_is_move or order.source.get_unit().order.destination != order.destination)
            ):
                return False, f"Supported unit {order.source} did not make corresponding order"

        return True, None

    return False, f"Unknown move type: {order.__class__.__name__}"


class MapperInformation:
    def __init__(self, unit: Unit):
        self.location = unit.location()
        self.order = unit.order


class Adjudicator:
    __metaclass__ = abc.ABCMeta

    def __init__(self, board: Board):
        self._board = board
        self.save_orders = True
        self.flags = board.data.get("adju flags", [])
        self.failed_or_invalid_units: set[MapperInformation] = set()

    @abc.abstractmethod
    def run(self) -> Board:
        pass


class BuildsAdjudicator(Adjudicator):
    def __init__(self, board: Board):
        super().__init__(board)

    def vassal_adju(self):
        for player in self._board.players:
            scs = 0
            for vassal in player.vassals:
                scs += len(vassal.centers)
            player.new_vassals = player.vassals.copy()
            if scs > len(player.centers):
                for order in player.vassal_orders.values():
                    if isinstance(order, Disown) and order.player in player.vassals:
                        player.new_vassals.remove(order.player)
                    scs2 = 0
                    for vassal in player.new_vassals:
                        scs2 += len(vassal.centers)
                    if scs2 > len(player.centers):
                        player.new_vassals = []
            else:
                for order in player.vassal_orders.values():
                    if isinstance(order, Vassal):
                        vassal = order.player
                        if player in vassal.vassal_orders and isinstance(vassal.vassal_orders[player], Liege):
                            if (not vassal.liege) or (vassal.liege in player.vassal_orders and isinstance(player.vassal_orders[vassal.liege], RebellionMarker)):
                                player.new_vassals.append(vassal)
                
        for player in self._board.players:
            new_liege = None
            overcommited = False
            for liege in self._board.players:
                if player in liege.new_vassals:
                    if new_liege is None:
                        new_liege = liege
                    else:
                        overcommited = True
                        break
            if overcommited:
                for liege in self._board.players:
                    if player in liege.new_vassals:
                        liege.new_vassals.remove(player)
            for order in player.vassal_orders:
                if isinstance(order, Defect):
                    if player in order.player.new_vassals:
                        order.player.new_vassals.remove(player)
                        new_liege = None
            player.new_liege = new_liege
            
        for player in self._board.players:
            player.liege = player.new_liege
            player.vassals = player.new_vassals
        
        for player in self._board.players:
            for order in player.vassal_orders.values():
                if isinstance(order, DualMonarchy) and player in order.player.vassal_orders and isinstance(order.player.vassal_orders[player], DualMonarchy):
                    other = order.player
                    if other.liege == None and not other.vassals and player.liege == None and not player.vassals:
                        other.vassals = [player]
                        player.vassals = [other]
                        other.liege = player
                        player.liege = other


        for player in self._board.players:
            player.points += len(player.centers)
            if not player.liege in player.vassals:
                for vassal in player.vassals:
                    player.points += len(vassal.centers)
                    for subvassal in vassal.vassals:
                        player.points += len(subvassal.centers)
            else:
                player.points += len(player.liege.centers)
                continue

            if player.liege:
                player.points += len(player.liege.centers) // 2


    def run(self) -> Board:
        for player in self._board.players:
            available_builds = len(player.centers) - len(player.units)
            if available_builds == 0:
                continue
            for order in player.build_orders:

                if available_builds > 0 and isinstance(order, Build):
                    coast = None
                    province = order.location
                    # ignore coast specifications for army
                    if isinstance(province, Coast):
                        if order.unit_type == UnitType.FLEET:
                            coast = province
                        province = province.province
                    if order.unit_type == UnitType.FLEET and coast == None:
                        logger.warning(f"Skipping {order}; someone tried to build a fleet not on the coast")
                        continue
                    if province.unit is not None:
                        logger.warning(f"Skipping {order}; there is already a unit there")
                        continue
                    if not province.has_supply_center or province.owner != player:
                        logger.warning(f"Skipping {order}; tried to build in non-sc, non-owned")
                        continue
                    if province.core != player and not "build anywhere" in self.flags:
                        logger.warning(f"Skipping {order}; tried to build in non-core")
                        continue
                    self._board.create_unit(order.unit_type, player, province, coast, None)
                    available_builds -= 1
                if available_builds < 0 and isinstance(order, Disband):
                    province = order.location.as_province()
                    if province.unit is None:
                        logger.warning(f"Skipping {order}; there is no unit there to disband")
                        continue
                    self._board.delete_unit(province)
                    available_builds += 1

                if available_builds < 0:
                    logger.warning(f"Player {player.name} disbanded less orders than they should have")

        if "vassal system" in self._board.data.get("adju flags", []):
            self.vassal_adju()




        for player in self._board.players:
            player.build_orders = set()
            player.waived_orders = 0
        return self._board


class RetreatsAdjudicator(Adjudicator):
    def __init__(self, board: Board):
        super().__init__(board)

    def run(self) -> Board:
        retreats_by_destination: dict[str, set[Unit]] = dict()
        units_to_delete: set[Unit] = set()
        for unit in self._board.units:
            if unit != unit.province.dislodged_unit:
                continue

            if unit.order is None:
                unit.order = NMR()
                
            if not isinstance(unit.order, RetreatMove):
                units_to_delete.add(unit)
                continue

            destination_province = unit.order.destination.as_province()
            if destination_province not in unit.retreat_options:
                units_to_delete.add(unit)
                continue

            if destination_province.name not in retreats_by_destination:
                retreats_by_destination[destination_province.name] = set()
            retreats_by_destination[destination_province.name].add(unit)

        for retreating_units in retreats_by_destination.values():
            if len(retreating_units) != 1:
                units_to_delete.update(retreating_units)
                continue

            (unit,) = retreating_units

            destination_coast = None
            destination_province = unit.order.destination
            if isinstance(unit.order.destination, Coast):
                destination_coast = unit.order.destination
                destination_province = destination_coast.province

            unit.province.dislodged_unit = None
            unit.province = destination_province
            unit.coast = destination_coast
            destination_province.unit = unit
            if not destination_province.has_supply_center or self._board.phase.name.startswith("Fall"):
                self._board.change_owner(destination_province, unit.player)

        for unit in units_to_delete:
            unit.player.units.remove(unit)
            self._board.units.remove(unit)
            unit.province.dislodged_unit = None

        for unit in self._board.units:
            unit.order = None
            unit.retreat_options = None

        if self._board.phase.name.startswith("Fall") and "vassal system" in self._board.data.get("adju flags", []):
            for player in self._board.players:
                if player.liege in player.vassals:
                    other = player.liege
                    if (not player.get_class() == PlayerClass.KINGDOM) or (not other.get_class() == PlayerClass.KINGDOM):
                        # Dual Monarchy breaks
                        for p in (player, other):
                            p.vassals = []
                            p.liege = None
                
                elif player.liege:
                    if player.liege.get_class().value <= player.get_class().value:
                        liege = player.liege
                        player.liege = None
                        liege.vassals.remove(player)
                        player.build_orders.add(RebellionMarker(liege))

            

        return self._board


class MovesAdjudicator(Adjudicator):
    # Algorithm from https://diplom.org/Zine/S2009M/Kruijswijk/DipMath_Chp6.htm
    def __init__(self, board: Board):
        super().__init__(board)
 
        self.orders: set[AdjudicableOrder] = set()

        # run supports after everything else since illegal cores / moves should be treated as holds
        units = sorted(board.units, key=lambda unit: isinstance(unit.order, Support))
        for unit in units:
            # Replace invalid orders with holds
            # Importantly, this includes supports for which the corresponding unit didn't make the same move
            # Same for convoys
            
            if unit.order is None:
                unit.order = NMR()

            failed: bool = False
            # indicates that an illegal move / core can't be support held
            not_supportable: bool = False

            # TODO clean up mapper info
            valid, reason = order_is_valid(unit.location(), unit.order, strict_convoys_supports=True)
            if not valid:
                logger.debug(f"Order for {unit} is invalid because {reason}")
                if isinstance(unit.order, Move) and unit.unit_type == UnitType.ARMY:
                    logger.debug("Retrying move order as ConvoyMove")
                    # TODO Runs duplicated code
                    valid, reason = order_is_valid(
                        unit.location(), ConvoyMove(unit.order.destination), strict_convoys_supports=False
                    )
                    if not valid:  # move is invalid in the first place, so it is a failed move
                        not_supportable = True
                        failed = True
                    else:
                        strict_valid, reason = order_is_valid(
                            unit.location(), ConvoyMove(unit.order.destination), strict_convoys_supports=True
                        )

                        if not strict_valid:  # move is valid but no convoy, so it is a failed move
                            not_supportable = True
                            failed = True
                        else:
                            unit.order = ConvoyMove(unit.order.destination)
                elif isinstance(unit.order, Core):
                    not_supportable = True
                    failed = True
                else:
                    failed = True

            order = AdjudicableOrder(unit)
            if failed:
                self.failed_or_invalid_units.add(MapperInformation(unit))
                order.is_valid = False
                unit.order.hasFailed = True
            if not_supportable:
                order.not_supportable = True

            self.orders.add(order)


        self.orders_by_province = {order.current_province.name: order for order in self.orders}
        self.moves_by_destination: dict[str, set[AdjudicableOrder]] = dict()
        for order in self.orders:
            if order.type == OrderType.MOVE:
                if order.destination_province.name not in self.moves_by_destination:
                    self.moves_by_destination[order.destination_province.name] = set()
                self.moves_by_destination[order.destination_province.name].add(order)

        for order in self.orders:
            if order.type == OrderType.SUPPORT:
                self.orders_by_province[order.source_province.name].supports.add(order)
            if order.type == OrderType.CONVOY:
                self.orders_by_province[order.source_province.name].convoys.add(order)

        self._dependencies: list[AdjudicableOrder] = []

        self._find_convoy_kidnappings()

    def _find_convoy_kidnappings(self):
        for order in self.orders:
            if order.type != OrderType.MOVE:
                continue

            if len(self.orders_by_province[order.source_province.name].convoys) == 0:
                continue

            # According to the 1971 ruling in DATC, the army only is kidnapped if
            # 1. the army's destination is moving back at it
            # 2.  the convoy isn't disrupted

            if order.destination_province.name in self.orders_by_province:
                attacked_order = self.orders_by_province[order.destination_province.name]
                if attacked_order.destination_province == order.source_province:
                    if self._adjudicate_convoys_for_order(order) == Resolution.SUCCEEDS:
                        order.is_convoy = True

    def run(self) -> Board:
        for order in self.orders:
            order.state = ResolutionState.UNRESOLVED
        for order in self.orders:
            self._resolve_order(order)
            order.base_unit.order.hasFailed = (order.resolution == Resolution.FAILS)
        if self.save_orders:
            database.get_connection().save_order_for_units(self._board, set(o.base_unit for o in self.orders))
        self._update_board()
        return self._board

    def _update_board(self):
        if not all(order.state == ResolutionState.RESOLVED for order in self.orders):
            raise RuntimeError("Cannot update board until all orders are resolved!")

        for order in self.orders:
            if order.type == OrderType.CORE and order.resolution == Resolution.SUCCEEDS:
                order.source_province.corer = order.country
            if order.type == OrderType.MOVE and order.resolution == Resolution.SUCCEEDS:
                logger.debug(f"Moving {order.source_province} to {order.destination_province}")
                if order.source_province.unit == order.base_unit:
                    order.source_province.unit = None
                if order.source_province.dislodged_unit == order.base_unit:
                    # We might have been dislodged by other move, but we shouldn't have been
                    order.source_province.dislodged_unit = None
                    order.base_unit.retreat_options = None
                # Dislodge whatever is there
                order.destination_province.dislodged_unit = order.destination_province.unit
                # see DATC 4.A.5
                if order.destination_province.dislodged_unit is not None:
                    order.destination_province.dislodged_unit.retreat_options = order.destination_province.adjacent.copy()
                    if not order.is_convoy:
                        order.destination_province.dislodged_unit.retreat_options -= {order.source_province}
                # Move us there
                order.base_unit.province = order.destination_province
                if isinstance(order.raw_destination, Coast):
                    order.base_unit.coast = order.raw_destination
                else:
                    order.base_unit.coast = None
                order.destination_province.unit = order.base_unit
                if not order.destination_province.has_supply_center or self._board.phase.name.startswith("Fall"):
                    self._board.change_owner(order.destination_province, order.country)
            if (order.type == OrderType.HOLD
                and order.resolution == Resolution.SUCCEEDS
                and order.source_province.dislodged_unit != order.base_unit):
                if not order.destination_province.has_supply_center or self._board.phase.name.startswith("Fall"):
                    self._board.change_owner(order.destination_province, order.country)

        for province in self._board.provinces:
            if province.corer:
                if province.half_core == province.corer:
                    province.core = province.corer
                    province.half_core = None
                else:
                    province.half_core = province.corer
            else:
                province.half_core = None
            province.corer = None

        contested = self._find_contested_areas()

        for unit in self._board.units:
            unit.order = None
            if unit.retreat_options is not None:
                unit.retreat_options -= contested
                if unit.unit_type == UnitType.ARMY:
                    unit.retreat_options = {x for x in unit.retreat_options if x.type != ProvinceType.SEA}
                else:
                    unit.retreat_options &= get_adjacent_provinces(unit.location())

            # Update provinces again to capture SCs in fall where units held
            if self._board.phase.name.startswith("Fall"):
                if unit.province.unit == unit and unit.province.owner != unit.player:
                    self._board.change_owner(unit.province, unit.player)

    def _find_contested_areas(self):
        bounces_and_occupied = set()
        for order in self.orders:
            if order.type == OrderType.MOVE:
                if order.is_convoy:
                    # unsuccessful convoys don't bounce
                    if order.resolution == Resolution.SUCCEEDS:
                        bounces_and_occupied.add(order.destination_province)
                else:
                    # TODO duplicated head on code
                    if order.destination_province.name in self.orders_by_province:
                        attacked_order = self.orders_by_province[order.destination_province.name]
                        if (
                            attacked_order.type == OrderType.MOVE
                            and attacked_order.destination_province == order.current_province
                        ):
                            # if this is a head on attack, and the unit lost the head on, then the area is not contested
                            head_on = not attacked_order.is_convoy and not order.is_convoy
                            if head_on and order.resolution == Resolution.FAILS:
                                continue

                    bounces_and_occupied.add(order.destination_province)

        for unit in self._board.units:
            bounces_and_occupied.add(unit.province)

        return bounces_and_occupied

    def _adjudicate_convoys_for_order(self, order: AdjudicableOrder) -> Resolution:
        # Breadth-first search to determine if there is a convoy connection for order.
        # Only considers it a success if it passes through at least one fleet to get to the destination
        assert order.type == OrderType.MOVE
        visited: set[str] = set()
        to_visit = collections.deque()
        to_visit.append(order.source_province)
        while 0 < len(to_visit):
            current = to_visit.popleft()
            # Have to pass through at least one convoying fleet
            if current != order.source_province and order.destination_province in current.adjacent:
                return Resolution.SUCCEEDS

            visited.add(current.name)

            adjacent_convoys = {
                convoy_order for convoy_order in order.convoys if convoy_order.current_province in current.adjacent
            }
            for convoy in adjacent_convoys:
                if convoy.current_province.name in visited:
                    continue
                if self._resolve_order(convoy) == Resolution.SUCCEEDS:
                    to_visit.append(convoy.current_province)
        return Resolution.FAILS

    def _adjudicate_order(self, order: AdjudicableOrder) -> Resolution:
        if order.type == OrderType.HOLD:
            # Resolution is arbitrary for holds; they don't do anything
            return Resolution.SUCCEEDS
        elif order.type == OrderType.CORE or order.type == OrderType.SUPPORT:
            # Both these orders fail if attacked by nation, even if that order isn't successful
            moves_here = self.moves_by_destination.get(order.current_province.name, set()) - {order}
            for move_here in moves_here:
                # coring should fail even if the attack comes from the same nation
                if move_here.country == order.country and order.type == OrderType.SUPPORT:
                    continue
                if not move_here.is_valid:
                    continue
                if not move_here.is_convoy:
                    if move_here.current_province != order.destination_province:
                        return Resolution.FAILS
                    else:
                        # If we are being attacked by the place we are supporting against,
                        # our support only fails if they succeed
                        if self._resolve_order(move_here) == Resolution.SUCCEEDS:
                            return Resolution.FAILS
                else:
                    # decide to fail convoys that cut support to their attack
                    if (
                        self._adjudicate_convoys_for_order(move_here) == Resolution.SUCCEEDS
                        and move_here.current_province != order.destination_province
                    ):
                        return Resolution.FAILS
            return Resolution.SUCCEEDS
        elif order.type == OrderType.CONVOY:
            moves_here = self.moves_by_destination.get(order.current_province.name, set())
            for move_here in moves_here:
                # see https://webdiplomacy.net/doc/DATC_v3_0.html#5.D
                if self._adjudicate_order(move_here) == Resolution.SUCCEEDS:
                    return Resolution.FAILS
            return Resolution.SUCCEEDS
        # Algorithm from https://diplom.org/Zine/S2009M/Kruijswijk/DipMath_Chp2.htm
        elif order.type == OrderType.MOVE:
            return self._adjudicate_move_order(order)

    def _adjudicate_move_order(self, order: AdjudicableOrder) -> Resolution:
        # check that convoy path work
        if order.is_convoy:
            if self._adjudicate_convoys_for_order(order) == Resolution.FAILS:
                return Resolution.FAILS

        # X -> Z, Y -> Z scenario, prevent strength
        orders_to_overcome = self.moves_by_destination[order.destination_province.name] - {order}
        # X -> Y, Y -> Z scenario
        attacked_order: AdjudicableOrder | None = None

        head_on = False
        if order.destination_province.name in self.orders_by_province:
            attacked_order = self.orders_by_province[order.destination_province.name]

            if attacked_order.type == OrderType.MOVE and attacked_order.destination_province == order.current_province:
                # only head on if not convoy
                head_on = not attacked_order.is_convoy and not order.is_convoy

        attack_strength = 1
        attacked_move = (
            attacked_order == None
            or attacked_order.type == OrderType.MOVE
            and self._resolve_order(attacked_order) == Resolution.SUCCEEDS
        )

        if head_on or not attacked_move:
            attacked_country = attacked_order.country

            if attacked_country == order.country:
                return Resolution.FAILS

            for support in order.supports:
                if self._resolve_order(support) == Resolution.SUCCEEDS and attacked_country != support.country:
                    attack_strength += 1

            opponent_strength = 1
            # count supports if it wasn't a failed move
            if head_on or (attacked_order.type != OrderType.MOVE and not attacked_order.not_supportable):
                for support in attacked_order.supports:
                    if self._resolve_order(support) == Resolution.SUCCEEDS:
                        opponent_strength += 1

            if attack_strength <= opponent_strength:
                return Resolution.FAILS
        else:
            for support in order.supports:
                if self._resolve_order(support) == Resolution.SUCCEEDS:
                    attack_strength += 1

            # If A -> B, and B beats C head on then C can't affect A
            if attacked_order != None:
                if not attacked_order.is_convoy:
                    orders_to_overcome = {
                        order
                        for order in orders_to_overcome
                        if order.source_province != attacked_order.destination_province or order.is_convoy
                    }

        for opponent in orders_to_overcome:
            if not opponent.is_valid:
                continue
            # don't need to overcome failed convoys
            if opponent.is_convoy and self._adjudicate_convoys_for_order(opponent) == Resolution.FAILS:
                continue
            prevent_strength = 1
            for support in opponent.supports:
                if self._resolve_order(support) == Resolution.SUCCEEDS:
                    prevent_strength += 1
            if attack_strength <= prevent_strength:
                return Resolution.FAILS

        return Resolution.SUCCEEDS

    def _resolve_order(self, order: AdjudicableOrder) -> Resolution:
        # logger.debug(f"Adjudicating order {order}")
        if order.state == ResolutionState.RESOLVED:
            return order.resolution

        if order.state == ResolutionState.GUESSING:
            if order not in self._dependencies:
                self._dependencies.append(order)
            return order.resolution
            
        if not order.is_valid:
            order.resolution = Resolution.FAILS
            order.state = ResolutionState.RESOLVED
            return order.resolution

        old_dependency_count = len(self._dependencies)
        # Guess that this fails
        order.resolution = Resolution.FAILS
        order.state = ResolutionState.GUESSING

        first_result = self._adjudicate_order(order)

        if old_dependency_count == len(self._dependencies):
            # Adjudication has not introduced new dependencies, see backup rule
            if order.state != ResolutionState.RESOLVED:
                order.resolution = first_result
                order.state = ResolutionState.RESOLVED
            return first_result

        if self._dependencies[old_dependency_count] != order:
            # We depend on a guess, but not our own guess
            self._dependencies.append(order)
            order.resolution = first_result
            # State remains Guessing
            return first_result

        # We depend on our own guess; reset all dependencies
        for other_unit in self._dependencies[old_dependency_count:]:
            other_unit.state = ResolutionState.UNRESOLVED
        self._dependencies = self._dependencies[:old_dependency_count]

        # Guess that this succeeds
        order.resolution = Resolution.SUCCEEDS
        order.state = ResolutionState.GUESSING

        second_result = self._adjudicate_order(order)

        if first_result == second_result:
            for other_unit in self._dependencies[old_dependency_count:]:
                other_unit.state = ResolutionState.UNRESOLVED
            self._dependencies = self._dependencies[:old_dependency_count]
            order.state = ResolutionState.RESOLVED
            order.resolution = first_result
            return first_result

        self._backup_rule(old_dependency_count)

        return self._resolve_order(order)

    def _backup_rule(self, old_dependency_count):
        # Deal with paradoxes and circular dependencies
        orders = self._dependencies[old_dependency_count:]
        self._dependencies = self._dependencies[:old_dependency_count]
        logger.warning(f"I think there's a move paradox involving these moves: {[str(x) for x in orders]}")
        # Szykman rule - If any of these orders is a convoy, fail the order
        apply_szykman = False
        for order in orders:
            if order.type == OrderType.CONVOY:
                apply_szykman = True
                break

        if apply_szykman:
            for order in orders:
                if order.type == OrderType.CONVOY:
                    order.resolution = Resolution.FAILS
                    order.state = ResolutionState.RESOLVED
                else:
                    order.state = ResolutionState.UNRESOLVED
            return
        # Circular dependencies
        for order in orders:
            if order.type == OrderType.MOVE:
                order.resolution = Resolution.SUCCEEDS
                order.state = ResolutionState.RESOLVED
            else:
                order.state = ResolutionState.UNRESOLVED


def make_adjudicator(board: Board) -> Adjudicator:
    if phase.is_moves(board.phase):
        return MovesAdjudicator(board)
    elif phase.is_retreats(board.phase):
        return RetreatsAdjudicator(board)
    elif phase.is_builds(board.phase):
        return BuildsAdjudicator(board)
    else:
        raise ValueError("Board is in invalid phase")
