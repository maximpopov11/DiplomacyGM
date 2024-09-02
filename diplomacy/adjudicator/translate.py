from collections import defaultdict

from pydip.map.map import Map as PydipMap, OwnershipMap, SupplyCenterMap
from pydip.player.command.adjustment_command import AdjustmentCreateCommand, AdjustmentDisbandCommand
from pydip.player.command.command import (
    Command as PydipCommand,
    ConvoyMoveCommand,
    ConvoyTransportCommand,
    HoldCommand,
    MoveCommand,
    SupportCommand,
)
from pydip.player.command.retreat_command import RetreatMoveCommand, RetreatDisbandCommand
from pydip.player.player import Player as PydipPlayer
from pydip.player.unit import Unit as PydipUnit, UnitTypes as PydipUnitType

from diplomacy.persistence.board import Board
from diplomacy.persistence.order import (
    ConvoyMove,
    ConvoyTransport,
    Hold,
    Move,
    Support,
    ComplexOrder,
    RetreatMove,
    RetreatDisband,
    Disband,
    Build,
)
from diplomacy.persistence.phase import is_moves_phase, fall_retreats
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, ProvinceType
from diplomacy.persistence.unit import UnitType, Unit


def get_territory_descriptors(provinces: set[Province]) -> list[dict[str, any]]:
    territory_descriptors = []
    for province in provinces:
        coasts: list[str] = []
        if province.coasts:
            for coast in province.coasts:
                coasts.append(coast.name)

        descriptor = {"name": province.name}
        # land provinces should have coasts set (empty for landlocked)
        # sea provinces should not have coasts set at all
        if province.type == ProvinceType.LAND or province.type == ProvinceType.ISLAND:
            descriptor["coasts"] = coasts

        territory_descriptors.append(descriptor)
    return territory_descriptors


def get_adjacencies(provinces: set[Province]) -> list[tuple[str, str]]:
    # we need to guarantee that there are no duplicates
    adjacencies = set()
    for province in provinces:
        # land/land and sea/sea adjacencies
        for province2 in province.adjacent:
            if province.type == province2.type:
                adjacencies.add(tuple(sorted((province.name, province2.name))))

        # coast/coast and coast/sea adjacencies
        for coast in province.coasts:
            for coast2 in coast.get_adjacent_coasts():
                adjacencies.add(tuple(sorted((coast.name, coast2.name))))
            for sea_province in coast.adjacent_seas:
                adjacencies.add(tuple(sorted((coast.name, sea_province.name))))

    return list(adjacencies)


def get_start_config(board: Board) -> dict[str, list[dict[str, str]]]:
    start_config = {}
    for player in board.players:
        player_config = []
        for unit in player.units:
            if unit.coast:
                territory_name = unit.coast.name
            else:
                territory_name = unit.province.name
                if unit.unit_type == UnitType.FLEET:
                    territory_name = list(unit.province.coasts)[0].name

            mapping = {
                "territory_name": territory_name,
                "unit_type": _get_pydip_unit_type(unit.unit_type),
            }
            player_config.append(mapping)
        start_config[player.name] = player_config
    return start_config


def get_players(
    players: set[Player],
    game_map: PydipMap,
    start_configs: dict[str, list[dict[str, str]]],
) -> dict[str, PydipPlayer]:
    pydip_players = {}
    for player in players:
        start_config = start_configs[player.name]
        pydip_player = PydipPlayer(player.name, game_map, start_config)
        pydip_players[player.name] = pydip_player
    return pydip_players


def get_units(board: Board) -> dict[str, set[PydipUnit]]:
    pydip_units = {}
    for province in board.provinces:
        unit = province.unit
        if unit:
            pydip_unit = _new_pydip_unit(province.unit)
            pydip_units.setdefault(unit.player.name, set()).add(pydip_unit)

        dislodged_unit = province.dislodged_unit
        if dislodged_unit:
            pydip_dislodged_unit = _new_pydip_unit(dislodged_unit)
            pydip_units.setdefault(dislodged_unit.player.name, set()).add(pydip_dislodged_unit)
    return pydip_units


def _new_pydip_unit(unit: Unit) -> PydipUnit:
    unit_type = _get_pydip_unit_type(unit.unit_type)
    location_name = unit.province.name
    if unit.coast:
        location_name = unit.coast.name
    return PydipUnit(unit_type, location_name)


def _get_pydip_unit_type(unit_type: UnitType) -> PydipUnitType:
    if unit_type == UnitType.ARMY:
        return PydipUnitType.TROOP
    elif unit_type == UnitType.FLEET:
        return PydipUnitType.FLEET
    else:
        raise ValueError(f"Illegal unit type {unit_type}.")


def _get_native_unit_type(unit_type: PydipUnitType) -> UnitType:
    if unit_type == PydipUnitType.TROOP:
        return UnitType.ARMY
    elif unit_type == PydipUnitType.FLEET:
        return UnitType.FLEET
    else:
        raise ValueError(f"Illegal unit type {unit_type}.")


def generate_retreats_map(
    pydip_players: dict[str, PydipPlayer],
    pydip_units: dict[str, set[PydipUnit]],
    board: Board,
) -> dict[PydipPlayer, dict[PydipUnit, set[str]]]:
    retreats_map = defaultdict(dict)
    for pydip_player in pydip_players:
        for pydip_unit in pydip_units[pydip_player]:
            location_name = pydip_unit.position
            province, _ = board.get_province_and_coast(location_name)
            dislodged_unit = province.dislodged_unit
            if dislodged_unit and dislodged_unit.player.name == pydip_player:
                # this should only hit on the dislodged unit, not on the primary unit in the province
                retreat_options_names: set[str] = {province.name for province in dislodged_unit.retreat_options}
                retreats_map[pydip_player][pydip_unit] = retreat_options_names
    return retreats_map


def get_commands(
    board: Board,
    pydip_players: dict[str, PydipPlayer],
    pydip_units: dict[str, set[PydipUnit]],
    retreats_map: dict[PydipPlayer, dict[PydipUnit, set[str]]],
    pydip_map: PydipMap,
) -> list[PydipCommand]:
    # TODO: (BETA) support core
    commands = []

    # unit orders
    for unit in board.units:
        order = unit.order

        if not order:
            if is_moves_phase(board.phase):
                # default to holds on moves phases because otherwise we can't tell what units exist because pydip return
                # doesn't give us the nicest data
                order = Hold()
            else:
                # if retreats or builds phase, don't give the unit an order and we're skipping
                continue

        pydip_unit = None
        pydip_player = pydip_players[unit.player.name]
        pydip_player_units = pydip_units[pydip_player.name]
        for pydip_candidate_unit in pydip_player_units:
            if _location_match(pydip_candidate_unit, unit):
                pydip_unit = pydip_candidate_unit
                break
        if not pydip_unit:
            raise RuntimeError(f"Pydip unit not found for unit with id {id(unit)}")

        source_unit = None
        if isinstance(order, ComplexOrder):
            pydip_player2 = pydip_players[order.source.player.name]
            player2_units = pydip_units[pydip_player2.name]

            for player2_unit in player2_units:
                if _location_match(player2_unit, order.source):
                    source_unit = player2_unit
            if source_unit is None:
                raise ValueError(
                    f"Secondary unit in order {order} with id {id(pydip_unit)} not found when connecting to pydip"
                )

        if isinstance(order, Hold):
            commands.append(HoldCommand(pydip_player, pydip_unit))
        elif isinstance(order, Move):
            commands.append(MoveCommand(pydip_player, pydip_unit, order.destination.name))
        elif isinstance(order, ConvoyMove):
            commands.append(ConvoyMoveCommand(pydip_player, pydip_unit, order.destination.name))
        elif isinstance(order, ConvoyTransport):
            commands.append(ConvoyTransportCommand(pydip_player, pydip_unit, source_unit, order.destination.name))
        elif isinstance(order, Support):
            commands.append(SupportCommand(pydip_player, pydip_unit, source_unit, order.destination.name))
        elif isinstance(order, RetreatMove):
            commands.append(RetreatMoveCommand(retreats_map, pydip_player, pydip_unit, order.destination.name))
        elif isinstance(order, RetreatDisband):
            commands.append(RetreatDisbandCommand(retreats_map, pydip_player, pydip_unit))
        else:
            raise ValueError(f"Order type {order.__class__} is not legal in {order}:")

    # build orders
    for player in board.players:
        for order in player.build_orders:
            pydip_player = pydip_players[order.location.get_owner().name]
            if isinstance(order, Build):
                ownership_map = get_ownership_map(pydip_map, board)
                new_unit = PydipUnit(_get_pydip_unit_type(order.unit_type), order.location.name)
                commands.append(AdjustmentCreateCommand(ownership_map, pydip_player, new_unit))
            elif isinstance(order, Disband):
                pydip_unit = None
                pydip_player = pydip_players[player.name]
                pydip_player_units = pydip_units[pydip_player.name]
                for pydip_candidate_unit in pydip_player_units:
                    if pydip_candidate_unit.position == order.location.name:
                        pydip_unit = pydip_candidate_unit
                        break
                if not pydip_unit:
                    raise RuntimeError(f"Pydip unit not found in {order.location.name}")

                commands.append(AdjustmentDisbandCommand(pydip_player, pydip_unit))
            else:
                raise ValueError(f"Order type {order.__class__} is not legal in {order}:")

    return commands


def _location_match(pydip_unit: PydipUnit, unit: Unit) -> bool:
    name = pydip_unit.position
    return name == unit.province.name or (unit.coast and name == unit.coast.name)


def get_ownership_map(pydip_map: PydipMap, board: Board) -> OwnershipMap:
    supply_centers = set()
    owned_territories = {}
    home_territories = {}

    for province in board.provinces:
        if province.has_supply_center:
            supply_centers.add(province.name)
            if province.core:
                player = province.owner
                if player:
                    home_territories.setdefault(player.name, set()).add(province.name)
                    owned_territories.setdefault(player.name, set()).add(province.name)

    supply_map = SupplyCenterMap(pydip_map, supply_centers)
    return OwnershipMap(supply_map, owned_territories, home_territories)


def get_adjustment_counts(board: Board) -> dict[str, int]:
    adjustment_counts = {}
    for player, count in board.get_build_counts():
        adjustment_counts[player] = count
    return adjustment_counts


def pydip_moves_to_native(board: Board, result_state: dict[str, dict[PydipUnit, set[str]]]) -> Board:
    board.phase = board.phase.next

    # result_state = dict[player_name, dict[pydip_unit, set[province_name]]
    # where pydip_unit is a unit that issued an order or a NEW unit if that unit moved
    # where set[province_name] is the set of retreat options or None if a unit does not need to retreat
    # pydip provides us new unit locations without telling us where the units came from, so despite how terrible it is
    # we delete all of our units and recreate them like what pydip does
    board.delete_all_units()
    for player_name, pydip_unit_to_retreats in result_state.items():
        for pydip_unit, retreat_options_names in pydip_unit_to_retreats.items():
            retreat_options: set[Province] | None = None
            if retreat_options_names:
                retreat_options: set[Province] = {board.get_province(name) for name in retreat_options_names}
            _create_unit(board, player_name, pydip_unit, retreat_options)

    # update non-center province ownership
    for province in board.provinces:
        if not province.has_supply_center:
            if province.unit:
                province.owner = province.unit.player

    return board


def pydip_retreats_to_native(board: Board, result_state: dict[str, set[PydipUnit]]) -> Board:
    board.phase = board.phase.next

    # result_state maps player names to a set of pydip units and only contains units that retreated
    # we delete all of our dislodged units and recreate them like what pydip does
    board.delete_dislodged_units()
    for player_name, pydip_units in result_state.items():
        for pydip_unit in pydip_units:
            _create_unit(board, player_name, pydip_unit, None)

    # update province ownership (centers only after Fall retreats)
    for province in board.provinces:
        if board.phase == fall_retreats or not province.has_supply_center:
            if province.unit:
                province.owner = province.unit.player

    return board


def pydip_adjustments_to_native(board: Board, result_state: dict[str, set[PydipUnit]]) -> Board:
    board.phase = board.phase.next

    # result_state is a dict of player name to the set of all of their units
    # since units do not move in this phase, we do not need to delete all units like in the other phases
    # but rather just correct the difference between what we have and what exists in pydip

    location_name_to_unit: dict[str, Unit] = {}
    for unit in board.units:
        location_name_to_unit[unit.get_location().name] = unit

    found_units = set()
    for player_name, pydip_units in result_state.items():
        for pydip_unit in pydip_units:
            unit = location_name_to_unit[pydip_unit.position]
            if not unit:
                # this is a new unit that was built
                _create_unit(board, player_name, pydip_unit, None)
            else:
                # we found the unit and shouldn't delete it later in this function
                found_units.add(unit)

    for unit in location_name_to_unit.values():
        if unit not in found_units:
            # this is a unit that were disbanded
            board.delete_unit(unit.province)

    return board


def _create_unit(board: Board, player_name: str, pydip_unit: PydipUnit, retreat_options: set[Province] | None) -> None:
    unit_type = _get_native_unit_type(pydip_unit.unit_type)
    player = board.get_player(player_name)
    province, coast = board.get_province_and_coast(pydip_unit.position)
    board.create_unit(unit_type, player, province, coast, retreat_options)
