from __future__ import annotations
from typing import List, Mapping, NoReturn, Optional, Set, TYPE_CHECKING

from pydip.map.map import Map as PydipMap
from pydip.player.player import Player as PydipPlayer
from pydip.player.unit import Unit as PydipUnit
from pydip.turn.adjustment import resolve_adjustment
from pydip.turn.resolve import resolve_turn
from pydip.turn.retreat import resolve_retreats

from diplomacy import phase
from diplomacy.board.board import Board
from diplomacy.persistence import translation
from diplomacy.persistence.mapper import Mapper
from diplomacy.phase import Phase
from diplomacy.player import Player
from diplomacy.province import Province

if TYPE_CHECKING:
    from diplomacy.order import Order


# TODO: (DB) if DB is not used, check that all persistence is saved to file
class Adjudicator:
    def __init__(self, board: Board):
        self.provinces: Set[Province] = board.provinces

        territory_descriptors = translation.get_territory_descriptors(self.provinces)
        adjacencies = translation.get_adjacencies(self.provinces)
        self.map: PydipMap = PydipMap(territory_descriptors, adjacencies)
        self.mapper: Mapper = Mapper(self.map)

        self.players: Set[Player] = board.players
        start_config: Mapping[
            str, List[Mapping[str, str]]
        ] = translation.get_start_config(board.players)
        self.pydip_players: Mapping[str, PydipPlayer] = translation.get_players(
            board.players, self.map, start_config
        )

        self.units = translation.get_units(board.provinces)
        self.phase: Phase = board.phase

        self.retreat_map: Optional[Mapping[PydipPlayer, Mapping[PydipUnit, str]]] = None

    def add_orders(self, orders: Set[Order]) -> NoReturn:
        # TODO: (DB) store orders in file in case we crash; make sure we overwrite old orders for unit
        pass

    def _get_orders(self) -> List[Order]:
        # TODO: (DB) get orders from file in case we crash
        pass

    def get_build_counts(self) -> Mapping[str, int]:
        return translation.get_adjustment_counts(self.players)

    def adjudicate(self) -> str:
        orders = self._get_orders()
        ownership_map = translation.get_ownership_map(self.map)
        commands = translation.get_commands(
            orders, self.pydip_players, self.units, self.retreat_map, ownership_map
        )

        if phase.is_moves_phase(self.phase):
            self.retreat_map = resolve_turn(self.map, commands)
        elif phase.is_retreats_phase(self.phase):
            resolve_retreats(self.map, commands)
        elif phase.is_adjustments_phase(self.phase):
            ownership_map = translation.get_ownership_map(self.provinces, self.map)
            adjustment_counts = self.get_build_counts()
            resolve_adjustment(ownership_map, adjustment_counts, self.units, commands)
        else:
            raise ValueError("Illegal phase:", self.phase)

        self.mapper = Mapper(self.map)
        moves_map = self.mapper.get_moves_map(None)
        results_map = self.mapper.get_results_map()
        # TODO: (MAP) return both SVGs
        raise RuntimeError("Adjudication has not yet been fully implemented.")

    def rollback(self) -> str:
        # TODO: (DB) implement rollback to last map
        raise RuntimeError(
            "Rollback will not be implemented until we have a server running the bot rather than a GM."
        )

    def get_player(self, name) -> Optional[Player]:
        for player in self.players:
            if player.name == name:
                return player
        return None
