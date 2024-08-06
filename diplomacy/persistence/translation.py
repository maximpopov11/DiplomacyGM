from typing import List, Mapping, Set, Tuple

from pydip.player.command.command import (
    Command as PydipCommand,
    ConvoyMoveCommand,
    ConvoyTransportCommand,
    HoldCommand,
    MoveCommand,
    SupportCommand,
)
from pydip.player.command.adjustment_command import (
    AdjustmentCreateCommand,
    AdjustmentDisbandCommand,
)
from pydip.map.map import Map as PydipMap, OwnershipMap, SupplyCenterMap
from pydip.player.command.retreat_command import (
    RetreatMoveCommand,
    RetreatDisbandCommand,
)
from pydip.player.player import Player as PydipPlayer
from pydip.player.unit import Unit as PydipUnit, UnitTypes as PydipUnitType

from diplomacy.order import (
    ConvoyMove,
    ConvoyTransport,
    Hold,
    Move,
    Support,
    ComplexOrder,
    RetreatMove,
    RetreatDisband,
    Order,
    Disband,
    UnitOrder,
    Build,
)
from diplomacy.player import Player
from diplomacy.province import Province
from diplomacy.unit import Army, Fleet, Unit


def get_territory_descriptors(provinces: Set[Province]) -> List[Mapping[str, any]]:
    territory_descriptors = []
    for province in provinces:
        coasts = []
        if not province.coasts:
            coasts.append({"name": f"{province.name} coast"})
        else:
            for coast in province.coasts:
                coasts.append({"name": coast.name})

        territory_descriptors.append(
            {
                "name": province.name,
                "coasts": coasts,
            }
        )
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
            mapping = {
                "territory_name": unit.province.name,
                "unit_type": _get_unit_type(unit),
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
            unit_type = _get_unit_type(province.unit)
            pydip_units.setdefault(province.unit.player.name, set()).add(
                PydipUnit(unit_type, province.name)
            )
    return pydip_units


def _get_unit_type(unit: Unit) -> PydipUnitType:
    if isinstance(unit, Army):
        return PydipUnitType.TROOP
    elif isinstance(unit, Fleet):
        return PydipUnitType.FLEET
    else:
        raise ValueError(
            f"Illegal unit type {unit.__class__} for unit in {unit.province.name}."
        )


def get_commands(
    orders: List[Order],
    pydip_players: Mapping[str, PydipPlayer],
    pydip_units: Mapping[str, Set[PydipUnit]],
    retreats_map: Mapping[PydipPlayer, Mapping[PydipUnit, str]],
    ownership_map: OwnershipMap,
) -> List[PydipCommand]:
    # TODO: (ALPHA) support core
    commands = []
    for order in orders:
        unit = None
        if isinstance(order, UnitOrder):
            pydip_player = pydip_players[order.unit.player.name]
            player_units = pydip_units[pydip_player.name]

            for pydip_unit in player_units:
                if pydip_unit.position == order.unit.province.name:
                    unit = pydip_unit
            if unit is None:
                raise ValueError(
                    f"Ordered unit at {order.unit.province.name} not found when connecting to adjudication"
                    " library."
                )
        elif isinstance(order, Build):
            pydip_player = pydip_players[order.province.owner.name]
        else:
            raise ValueError(f"Illegal order type: {order.__class__}")

        source_unit = None
        if isinstance(order, ComplexOrder):
            pydip_player2 = pydip_players[order.source.player.name]
            player2_units = pydip_units[pydip_player2.name]

            for player2_unit in player2_units:
                if player2_unit.position == order.source.province.name:
                    source_unit = player2_unit
            if source_unit is None:
                raise ValueError(
                    f"Secondary unit in order {order} at {order.unit.province.name} not found when "
                    "connecting to adjudication library."
                )

        if isinstance(order, Hold):
            commands.append(HoldCommand(pydip_player, unit))
        elif isinstance(order, Move):
            commands.append(MoveCommand(pydip_player, unit, order.destination))
        elif isinstance(order, ConvoyMove):
            commands.append(ConvoyMoveCommand(pydip_player, unit, order.destination))
        elif isinstance(order, ConvoyTransport):
            commands.append(
                ConvoyTransportCommand(
                    pydip_player, unit, source_unit, order.destination
                )
            )
        elif isinstance(order, Support):
            commands.append(
                SupportCommand(pydip_player, unit, source_unit, order.destination)
            )
        elif isinstance(order, RetreatMove):
            commands.append(
                RetreatMoveCommand(retreats_map, pydip_player, unit, order.destination)
            )
        elif isinstance(order, RetreatDisband):
            commands.append(RetreatDisbandCommand(retreats_map, pydip_player, unit))
        elif isinstance(order, Build):
            new_unit = PydipUnit(_get_unit_type(order.unit), order.province.name)
            commands.append(
                AdjustmentCreateCommand(ownership_map, pydip_player, new_unit)
            )
        elif isinstance(order, Disband):
            commands.append(AdjustmentDisbandCommand(pydip_player, unit))
        else:
            raise ValueError(
                f"Order type {order.__class__} is not legal for order:", order
            )

    return commands


def get_ownership_map(provinces: Set[Province], pydip_map: PydipMap) -> OwnershipMap:
    supply_centers = set()
    owned_territories = {}
    home_territories = {}

    for province in provinces:
        if province.has_supply_center:
            supply_centers.add(province.name)
            if province.core:
                home_territories.setdefault(province.owner, set()).add(province.name)
                if province.owner:
                    owned_territories.setdefault(province.owner, set()).add(
                        province.name
                    )

    supply_map = SupplyCenterMap(pydip_map, supply_centers)
    return OwnershipMap(supply_map, owned_territories, home_territories)


def get_adjustment_counts(players: Set[Player]) -> Mapping[str, int]:
    adjustment_counts = {}
    for player in players:
        adjustment_counts[player.name] = len(player.centers) - len(player.units)
    return adjustment_counts
