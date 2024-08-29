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
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, ProvinceType
from diplomacy.persistence.unit import UnitType


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
    adjacencies: set[tuple[str, str]] = set()
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
            unit_type = _get_pydip_unit_type(unit.unit_type)
            pydip_units.setdefault(unit.player.name, set()).add(PydipUnit(unit_type, province.name))
    return pydip_units


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
    provinces: set[Province],
) -> dict[PydipPlayer, dict[PydipUnit, set[str]]]:
    names_to_provinces: dict[str, Province] = {province.name: province for province in provinces}
    retreats_map = defaultdict()
    for pydip_player in pydip_players:
        for pydip_unit in pydip_units[pydip_player]:
            province_name = pydip_unit.position
            dislodged_unit = names_to_provinces[province_name].dislodged_unit
            if dislodged_unit:
                retreats_map[pydip_unit] = dislodged_unit.retreat_options
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

        pydip_unit = None
        pydip_player = pydip_players[unit.player.name]
        pydip_player_units = pydip_units[pydip_player.name]
        for pydip_candidate_unit in pydip_player_units:
            if pydip_candidate_unit.position == unit.province.name:
                pydip_unit = pydip_candidate_unit
                break
        if not pydip_unit:
            raise RuntimeError(f"Pydip unit not found for unit with id {id(unit)}")

        source_unit = None
        if isinstance(order, ComplexOrder):
            pydip_player2 = pydip_players[order.source.player.name]
            player2_units = pydip_units[pydip_player2.name]

            for player2_unit in player2_units:
                if player2_unit.position == order.source.province.name:
                    source_unit = player2_unit
            if source_unit is None:
                raise ValueError(
                    f"Secondary unit in order {order} with id {id(pydip_unit)} not found when connecting to adjudication "
                    "library."
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
        elif isinstance(order, Disband):
            commands.append(AdjustmentDisbandCommand(pydip_player, pydip_unit))
        else:
            raise ValueError(f"Order type {order.__class__} is not legal in {order}:")

    # build orders
    for player in board.players:
        for order in player.build_orders:
            pydip_player = pydip_players[order.province.owner.name]

            if isinstance(order, Build):
                ownership_map = get_ownership_map(pydip_map, board)
                new_unit = PydipUnit(_get_pydip_unit_type(order.unit_type), order.province.name)
                commands.append(AdjustmentCreateCommand(ownership_map, pydip_player, new_unit))
            else:
                raise ValueError(f"Order type {order.__class__} is not legal in {order}:")

    return commands


def get_ownership_map(pydip_map: PydipMap, board: Board) -> OwnershipMap:
    supply_centers = set()
    owned_territories = {}
    home_territories = {}

    for province in board.provinces:
        if province.has_supply_center:
            supply_centers.add(province.name)
            if province.core:
                player = province.owner
                home_territories.setdefault(player.name, set()).add(province.name)
                if player:
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
            unit_type = _get_native_unit_type(pydip_unit.unit_type)
            player = board.get_player(player_name)
            # TODO: (!) make province and coast work for coastal units
            province = board.get_province(pydip_unit.position)
            coast = None
            retreat_options: set[Province] | None = None
            if retreat_options_names:
                retreat_options: set[Province] = {board.get_province(name) for name in retreat_options_names}
            board.create_unit(unit_type, player, province, coast, retreat_options)

    return board


def pydip_retreats_to_native(board: Board, result_state: None) -> Board:
    board.phase = board.phase.next
    # TODO: (!) implement
    pass


def pydip_adjustments_to_native(board: Board, result_state: None) -> Board:
    board.phase = board.phase.next
    # TODO: (!) implement, reset build orders
    pass
