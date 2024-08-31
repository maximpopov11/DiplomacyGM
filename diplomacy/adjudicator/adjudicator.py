from pydip.map.map import Map as PydipMap
from pydip.player.command.command import Command as PydipCommand
from pydip.player.player import Player as PydipPlayer
from pydip.player.unit import Unit as PydipUnit
from pydip.turn.adjustment import resolve_adjustment
from pydip.turn.resolve import resolve_turn
from pydip.turn.retreat import resolve_retreats

from diplomacy.adjudicator import translate
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.phase import Phase


class Adjudicator:
    def __init__(self, board: Board):
        self.board: Board = board

        territory_descriptors = translate.get_territory_descriptors(self.board.provinces)
        adjacencies = translate.get_adjacencies(self.board.provinces)
        self.pydip_map: PydipMap = PydipMap(territory_descriptors, adjacencies)

        start_config: dict[str, list[dict[str, str]]] = translate.get_start_config(self.board)
        self.pydip_players: dict[str, PydipPlayer] = translate.get_players(
            self.board.players,
            self.pydip_map,
            start_config,
        )

        self.pydip_units: dict[str, set[PydipUnit]] = translate.get_units(self.board)
        self.retreat_map: dict[PydipPlayer, dict[PydipUnit, set[str]]] = translate.generate_retreats_map(
            self.pydip_players,
            self.pydip_units,
            self.board,
        )
        self.pydip_commands: list[PydipCommand] = translate.get_commands(
            self.board,
            self.pydip_players,
            self.pydip_units,
            self.retreat_map,
            self.pydip_map,
        )
        self.phase: Phase = self.board.phase

    def adjudicate(self) -> Board:
        if phase.is_moves_phase(self.phase):
            return translate.pydip_moves_to_native(
                self.board,
                resolve_turn(self.pydip_map, self.pydip_commands),
            )
        elif phase.is_retreats_phase(self.phase):
            return translate.pydip_retreats_to_native(
                self.board,
                resolve_retreats(self.retreat_map, self.pydip_commands),
            )
        elif phase.is_adjustments_phase(self.phase):
            ownership_map = translate.get_ownership_map(self.pydip_map, self.board)
            adjustment_counts = translate.get_adjustment_counts(self.board)
            return translate.pydip_adjustments_to_native(
                self.board,
                resolve_adjustment(ownership_map, adjustment_counts, self.pydip_units, self.pydip_commands),
            )
        else:
            raise ValueError(f"Illegal phase: {self.phase.name}")
