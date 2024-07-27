from typing import List, Mapping, Tuple

from pydip.map.map import Map as Map
from pydip.player.command.command import MoveCommand, ConvoyMoveCommand, ConvoyTransportCommand, Command
from pydip.player.player import Player
from pydip.player.unit import UnitTypes
from pydip.turn.adjustment import resolve_adjustment
from pydip.turn.resolve import resolve_turn
from pydip.turn.retreat import resolve_retreats

from diplomacy import phase
from diplomacy.board.board import Board
from diplomacy.order import Order
from diplomacy.province import Province

game_master = 'GM'


class Adjudicator:
    def __init__(self, board: Board):
        provinces = board.provinces
        territory_descriptors = _get_territory_descriptors(provinces)
        adjacencies = _get_adjacencies(provinces)
        self.map = Map(territory_descriptors, adjacencies)
        self.phase = board.phase

    def adjudicate(self, orders: List[Order]) -> str:
        commands = _get_commands(orders)
        if phase.is_moves_phase(self.phase):
            resolve_turn(self.map, commands)
        elif phase.is_retreats_phase(self.phase):
            resolve_retreats(self.map, commands)
        elif phase.is_adjustments_phase(self.phase):
            resolve_adjustment(ownership_map, adjustment_counts, player_units, commands)
        else:
            raise ValueError('Illegal phase:', self.phase)

        # TODO: (IMPL) output new map
        return 'Pretend this is the moves map and the adjudication map!'

    def rollback(self) -> str:
        # TODO: (IMPL) implement
        return 'Pretend we rolled back the map to the last version!'


def _get_territory_descriptors(provinces: List[Province]) -> List[Mapping[str, any]]:
    # TODO: (IMPL) 'name': String, 'coasts': [ { 'name': String } ] (Optional)
    pass


def _get_adjacencies(provinces: List[Province]) -> List[Tuple[str, str]]:
    # TODO: (IMPL) implement: land/land and coast/coast and coast/sea and sea/sea only
    pass


def _get_commands(orders: List[Order]) -> List[Command]:
    # TODO: (IMPL) orders -> CommandMap

    italy_units = [
        {'territory_name': 'Rome', 'unit_type': UnitTypes.TROOP},
        {'territory_name': 'Ionian Sea', 'unit_type': UnitTypes.FLEET},
    ]
    italy = Player("Italy", self.map, italy_units)
    turkey_units = [
        {'territory_name': 'Naples', 'unit_type': UnitTypes.TROOP},
    ]
    turkey = Player("Turkey", self.map, turkey_units)

    commands = [
        ConvoyMoveCommand(italy, italy.units[0], 'Naples'),
        ConvoyTransportCommand(italy, italy.units[1], italy.units[0], 'Naples'),
        MoveCommand(turkey, turkey.units[0], 'Rome'),
    ]

    pass
