from typing import List, Mapping, Set, Tuple, NoReturn

from pydip.map.map import Map as Map
from pydip.player.command.command import MoveCommand, ConvoyMoveCommand, ConvoyTransportCommand, Command, HoldCommand, \
    SupportCommand
from pydip.player.player import Player
from pydip.player.unit import UnitTypes
from pydip.turn.adjustment import resolve_adjustment
from pydip.turn.resolve import resolve_turn
from pydip.turn.retreat import resolve_retreats

from diplomacy import phase
from diplomacy.board.board import Board
from diplomacy.order import Order, Hold, ConvoyTransport, Move, Support, InteractingOrder, ConvoyMove
from diplomacy.persistence.mapper import Mapper
from diplomacy.player import Player as InternalPlayer
from diplomacy.province import Province
from diplomacy.unit import Army, Fleet


class Adjudicator:
    def __init__(self):
        self.provinces = None
        self.map = None
        self.unit_config = None
        self.players = None
        self.phase = None

    def set_board(self, board: Board):
        provinces = board.provinces
        self.provinces = {province.name: province for province in provinces}
        territory_descriptors = _get_territory_descriptors(provinces)
        adjacencies = _get_adjacencies(board.adjacencies)
        self.map = Map(territory_descriptors, adjacencies)
        self.unit_config = _get_unit_config(board.players)
        self.players = _get_players(board.players, self.map, self.unit_config)
        self.phase = board.phase

    def add_orders(self, orders: Set[Order]) -> NoReturn:
        # TODO: (1) store orders in file in case we crash
        pass

    def _get_orders(self) -> List[Order]:
        # TODO: (1) get orders from file in case we crash
        pass

    def adjudicate(self) -> str:
        orders = self._get_orders()
        commands = _get_commands(orders, self.players, self.unit_config)
        if phase.is_moves_phase(self.phase):
            resolve_turn(self.map, commands)
        elif phase.is_retreats_phase(self.phase):
            resolve_retreats(self.map, commands)
        elif phase.is_adjustments_phase(self.phase):
            # TODO: (1) implement adjustments
            resolve_adjustment(ownership_map, adjustment_counts, player_units, commands)
        else:
            raise ValueError('Illegal phase:', self.phase)

        mapper = Mapper(self.map)
        moves_map = mapper.get_moves_map()
        results_map = mapper.get_results_map()
        # TODO: (1) return both SVGs
        return 'Pretend this is the moves map and the adjudication map!'

    def rollback(self) -> str:
        # TODO: (2) implement rollback to last map
        return 'Pretend we rolled back the map to the last version!'


def _get_territory_descriptors(provinces: List[Province]) -> List[Mapping[str, any]]:
    # TODO: (1) implement: 'name': String, 'coasts': [ { 'name': String } ] (Optional) (waiting on GM sea provinces)
    pass


def _get_adjacencies(adjacencies: Set[Tuple[str, str]]) -> List[Tuple[str, str]]:
    # TODO: (1) implement: land/land and coast/coast and coast/sea and sea/sea only (waiting on GM sea provinces)
    pass


def _get_unit_config(players: Set[InternalPlayer]) -> Mapping[str, List[Mapping[str, str]]]:
    unit_config = {}
    for player in players:
        player_config = []
        for unit in player.units:
            if isinstance(unit, Army):
                unit_type = UnitTypes.TROOP
            elif isinstance(unit, Fleet):
                unit_type = UnitTypes.FLEET
            else:
                raise ValueError('Unit type is not legal:', unit.__class__)

            mapping = {
                'territory_name': unit.province.name,
                'unit_type': unit_type,
            }
            player_config.append(mapping)
        unit_config[player.name] = player_config
    return unit_config


def _get_players(
        internal_players: Set[InternalPlayer],
        game_map: Map,
        start_configs: Mapping[str, List[Mapping[str, str]]],
) -> Mapping[str, Player]:
    players = {}
    for internal_player in internal_players:
        start_config = start_configs[internal_player.name]
        external_player = Player(name=internal_player.name, game_map=game_map, starting_configuration=start_config)
        players[internal_player.name] = external_player
    return players


def _get_commands(
        orders: List[Order],
        players: Mapping[str, Player],
        unit_config: Mapping[str, List[Mapping[str, str]]],
) -> List[Command]:
    commands = []
    for order in orders:
        commands.append(_order_to_command(order, players, unit_config))
    return commands


def _order_to_command(
        order: Order,
        players: Mapping[str, Player],
        unit_config: Mapping[str, List[Mapping[str, str]]],
) -> Command:
    player = players[order.unit.player.name]
    player_units = unit_config[player.name]
    province = order.unit.province.name
    unit = None
    for player_unit in player_units:
        if player_unit.get('territory_name') == province:
            unit = player_unit
    if unit is None:
        raise ValueError('Ordered unit not found when connecting to adjudication library.')

    unit2 = None
    if isinstance(order, InteractingOrder):
        player2 = players[order.source.player.name]
        player2_units = unit_config[player2.name]
        province2 = order.source.province
        for player2_unit in player2_units:
            if player2_unit.get('territory_name') == province2:
                unit2 = player2_unit
        if unit2 is None:
            raise ValueError('Secondary unit in order not found when connecting to adjudication library.')

    if isinstance(order, Hold):
        return HoldCommand(player, unit)
    elif isinstance(order, Move):
        return MoveCommand(player, unit, order.destination)
    elif isinstance(order, ConvoyMove):
        return ConvoyMoveCommand(player, unit, order.destination)
    elif isinstance(order, ConvoyTransport):
        return ConvoyTransportCommand(player, unit, unit2, order.destination)
    elif isinstance(order, Support):
        return SupportCommand(player, unit, unit2, order.destination)
    else:
        raise ValueError('Order type is not legal:', order.__class__)
