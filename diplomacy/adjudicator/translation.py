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
    UnitOrder,
    Build,
)
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, ProvinceType
from diplomacy.persistence.unit import UnitType


def get_territory_descriptors(provinces: set[Province]) -> list[dict[str, any]]:
    territory_descriptors = []
    for province in provinces:
        coasts = []
        if province.coasts:
            for coast in province.coasts:
                coasts.append({"name": coast.name})

        descriptor = {"name": province.name}
        # land provinces should have coasts set (empty for landlocked)
        # sea provinces should not have coasts set at all
        if province.type == ProvinceType.LAND or province.type == ProvinceType.ISLAND:
            descriptor["coasts"] = coasts

        territory_descriptors.append(descriptor)
    return territory_descriptors


def get_adjacencies(provinces: set[Province]) -> list[tuple[str, str]]:
    # TODO: this will find land/sea adjacencies in the first block, we need to not allow that
    # we need to guarantee that there are no duplicates
    adjacencies: set[tuple] = set()
    for province in provinces:
        # land/land and sea/sea adjacencies
        for province2 in province.adjacent:
            if province.type == province2.type:
                adjacencies.add(tuple(sorted((province.name, province2.name))))

        # coast/coast and coast/sea adjacencies
        for coast in province.coasts:
            for coast2 in coast.adjacent_coasts:
                adjacencies.add(tuple(sorted((coast.name, coast2.name))))
            for sea_province in coast.adjacent_seas:
                adjacencies.add(tuple(sorted((coast.name, sea_province.name))))

    return list(adjacencies)


# pydip wants unit province and type info for each player
def get_start_config(board: Board) -> dict[str, list[dict[str, str]]]:
    start_config = {}
    for player in board.players:
        player_config = []
        for unit in player.units:
            mapping = {
                "territory_name": board.get_province(unit).name,
                "unit_type": _get_unit_type(unit.unit_type),
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
        unit = board.get_unit(province)
        if unit:
            player = board.get_player(unit)
            unit = board.get_unit(province)
            unit_type = _get_unit_type(unit.unit_type)
            pydip_units.setdefault(player.name, set()).add(PydipUnit(unit_type, province.name))
    return pydip_units


def _get_unit_type(unit_type: UnitType) -> PydipUnitType:
    if unit_type == UnitType.ARMY:
        return PydipUnitType.TROOP
    elif unit_type == UnitType.FLEET:
        return PydipUnitType.FLEET
    else:
        raise ValueError(f"Illegal unit type {unit_type}.")


def get_commands(
    board: Board,
    pydip_players: dict[str, PydipPlayer],
    pydip_units: dict[str, set[PydipUnit]],
    retreats_map: dict[PydipPlayer, dict[PydipUnit, str]],
    pydip_map: PydipMap,
) -> list[PydipCommand]:
    # TODO: (ALPHA) support core
    commands = []
    for order in board.get_orders():
        unit = None
        if isinstance(order, UnitOrder):
            player = order.unit.player
            pydip_player = pydip_players[player.name]
            player_units = pydip_units[pydip_player.name]

            for pydip_unit in player_units:
                province = order.unit.province
                if pydip_unit.position == province.name:
                    unit = pydip_unit
            if unit is None:
                raise ValueError(f"Ordered unit with id {id(unit)} not found when connecting to adjudication library.")
        elif isinstance(order, Build):
            player = order.province.owner
            pydip_player = pydip_players[player.name]
        else:
            raise ValueError(f"Illegal order type: {order.__class__}")

        source_unit = None
        if isinstance(order, ComplexOrder):
            player_2 = order.source.player
            pydip_player2 = pydip_players[player_2.name]
            player2_units = pydip_units[pydip_player2.name]

            for player2_unit in player2_units:
                province = order.source.province
                if player2_unit.position == province.name:
                    source_unit = player2_unit
            if source_unit is None:
                raise ValueError(
                    f"Secondary unit in order {order} with id {id(unit)} not found when connecting to adjudication "
                    "library."
                )

        if isinstance(order, Hold):
            commands.append(HoldCommand(pydip_player, unit))
        elif isinstance(order, Move):
            commands.append(MoveCommand(pydip_player, unit, order.destination))
        elif isinstance(order, ConvoyMove):
            commands.append(ConvoyMoveCommand(pydip_player, unit, order.destination))
        elif isinstance(order, ConvoyTransport):
            commands.append(ConvoyTransportCommand(pydip_player, unit, source_unit, order.destination))
        elif isinstance(order, Support):
            commands.append(SupportCommand(pydip_player, unit, source_unit, order.destination))
        elif isinstance(order, RetreatMove):
            commands.append(RetreatMoveCommand(retreats_map, pydip_player, unit, order.destination))
        elif isinstance(order, RetreatDisband):
            commands.append(RetreatDisbandCommand(retreats_map, pydip_player, unit))
        elif isinstance(order, Build):
            ownership_map = get_ownership_map(pydip_map, board)
            new_unit = PydipUnit(_get_unit_type(order.unit_type), order.province.name)
            commands.append(AdjustmentCreateCommand(ownership_map, pydip_player, new_unit))
        elif isinstance(order, Disband):
            commands.append(AdjustmentDisbandCommand(pydip_player, unit))
        else:
            raise ValueError(f"Order type {order.__class__} is not legal for order:", order)

    return commands


def get_ownership_map(pydip_map: PydipMap, board: Board) -> OwnershipMap:
    supply_centers = set()
    owned_territories = {}
    home_territories = {}

    for province in board.provinces:
        if province.has_supply_center:
            supply_centers.add(province.name)
            if province.core:
                player = board.get_owner(province)
                home_territories.setdefault(player, set()).add(province.name)
                player = board.get_owner(province)
                if player:
                    owned_territories.setdefault(player, set()).add(province.name)

    supply_map = SupplyCenterMap(pydip_map, supply_centers)
    return OwnershipMap(supply_map, owned_territories, home_territories)


# TODO: command already does this, do we want a board function for it?
def get_adjustment_counts(board: Board) -> dict[str, int]:
    adjustment_counts = {}
    for player in board.players:
        provinces = player.centers
        num_centers = sum(province.has_supply_center for province in provinces)
        num_units = len(player.units)
        adjustment_counts[player.name] = num_centers - num_units
    return adjustment_counts
