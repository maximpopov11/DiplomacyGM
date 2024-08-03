from typing import List, Mapping, Set, Tuple

from pydip.player.command.command import Command as PydipCommand, ConvoyMoveCommand, ConvoyTransportCommand, \
    HoldCommand, MoveCommand, SupportCommand
from pydip.map.map import Map as PydipMap, OwnershipMap, SupplyCenterMap
from pydip.player.player import Player as PydipPlayer
from pydip.player.unit import Unit as PydipUnit, UnitTypes as PydipUnitTypes

from diplomacy.order import ConvoyMove, ConvoyTransport, Hold, Move, Order, Support, ComplexOrder
from diplomacy.player import Player
from diplomacy.province import Province
from diplomacy.unit import Army, Fleet


def get_territory_descriptors(provinces: Set[Province]) -> List[Mapping[str, any]]:
    territory_descriptors = []
    for province in provinces:
        coasts = []
        if not province.coasts:
            coasts.append({'name': f'{province.name} coast'})
        else:
            for coast in province.coasts:
                coasts.append({'name': coast.name})

        territory_descriptors.append({
            'name': province.name,
            'coasts': coasts,
        })
    return territory_descriptors


def get_adjacencies(provinces: Set[Province]) -> List[Tuple[str, str]]:
    # we need to guarantee that there are no duplicates
    adjacencies: Set[Tuple] = set()
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


def get_start_config(players: Set[Player]) -> Mapping[str, List[Mapping[str, str]]]:
    start_config = {}
    for player in players:
        player_config = []
        for unit in player.units:
            if isinstance(unit, Army):
                unit_type = PydipUnitTypes.TROOP
            elif isinstance(unit, Fleet):
                unit_type = PydipUnitTypes.FLEET
            else:
                raise ValueError('Unit type is not legal:', unit.__class__)

            mapping = {
                'territory_name': unit.province.name,
                'unit_type': unit_type,
            }
            player_config.append(mapping)
        start_config[player.name] = player_config
    return start_config


def get_players(
        players: Set[Player],
        game_map: PydipMap,
        start_configs: Mapping[str, List[Mapping[str, str]]],
) -> Mapping[str, PydipPlayer]:
    pydip_players = {}
    for player in players:
        start_config = start_configs[player.name]
        pydip_player = PydipPlayer(player.name, game_map, start_config)
        pydip_players[player.name] = pydip_player
    return pydip_players


def get_units(provinces: Set[Province]) -> Mapping[str, Set[PydipUnit]]:
    pydip_units = {}
    for province in provinces:
        if province.unit:
            player = province.unit.player.name
            if player not in pydip_units:
                pydip_units[player] = set()

            if isinstance(province.unit, Army):
                unit_type = PydipUnitTypes.TROOP
            elif isinstance(province.unit, Fleet):
                unit_type = PydipUnitTypes.FLEET
            else:
                raise ValueError(f'Illegal unit type {province.unit.__class__} for unit in {province.name}.')

            pydip_units[player].add(PydipUnit(unit_type, province.name))
    return pydip_units


def get_commands(
        orders: List[Order],
        pydip_players: Mapping[str, PydipPlayer],
        pydip_units: Mapping[str, Set[PydipUnit]],
) -> List[PydipCommand]:
    commands = []
    for order in orders:
        pydip_player = pydip_players[order.unit.player.name]
        player_units = pydip_units[pydip_player.name]

        unit = None
        for pydip_unit in player_units:
            if pydip_unit.position == order.unit.province.name:
                unit = pydip_unit
        if unit is None:
            raise ValueError(f'Ordered unit at {order.unit.province.name} not found when connecting to adjudication '
                             'library.')

        source_unit = None
        if isinstance(order, ComplexOrder):
            pydip_player2 = pydip_players[order.source.player.name]
            player2_units = pydip_units[pydip_player2.name]

            for player2_unit in player2_units:
                if player2_unit.position == order.source.province.name:
                    source_unit = player2_unit
            if source_unit is None:
                raise ValueError(f'Secondary unit in order {order} at {order.unit.province.name} not found when '
                                 'connecting to adjudication library.')

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
        else:
            raise ValueError(f'Order type {order.__class__} is not legal for order:', order)

    return commands


def get_ownership_map(provinces: Set[Province], pydip_map: PydipMap) -> OwnershipMap:
    supply_centers = set()
    owned_territories = {}
    home_territories = {}

    for province in provinces:
        if province.has_supply_center:
            supply_centers.add(province.name)

            if province.owner not in owned_territories:
                owned_territories[province.owner] = set()
            owned_territories[province.owner].add(province.name)

            if province.core is not None:
                if province.owner not in home_territories:
                    home_territories[province.owner] = set()
                home_territories[province.owner].add(province.name)

    supply_map = SupplyCenterMap(pydip_map, supply_centers)
    return OwnershipMap(supply_map, owned_territories, home_territories)


def get_adjustment_counts(players: Set[Player]) -> Mapping[str, int]:
    adjustment_counts = {}
    for player in players:
        adjustment_counts[player.name] = len(player.centers) - len(player.units)
    return adjustment_counts
