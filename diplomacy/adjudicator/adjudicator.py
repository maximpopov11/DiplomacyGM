from pydip.map.map import Map as PydipMap
from pydip.player.command.command import Command as PydipCommand
from pydip.player.player import Player as PydipPlayer
from pydip.player.unit import Unit as PydipUnit
from pydip.turn.adjustment import resolve_adjustment
from pydip.turn.resolve import resolve_turn
from pydip.turn.retreat import resolve_retreats

from diplomacy.adjudicator import translation
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.phase import Phase


class Adjudicator:
    def __init__(self, board: Board):
        self.board: Board = board

        territory_descriptors = translation.get_territory_descriptors(self.board.provinces)
        adjacencies = translation.get_adjacencies(self.board.provinces)
        self.pydip_map: PydipMap = PydipMap(territory_descriptors, adjacencies)

        start_config: dict[str, list[dict[str, str]]] = translation.get_start_config(self.board)
        self.pydip_players: dict[str, PydipPlayer] = translation.get_players(
            self.board.players,
            self.pydip_map,
            start_config,
        )

        self.pydip_units: dict[str, set[PydipUnit]] = translation.get_units(self.board)
        self.retreat_map: dict[PydipPlayer, dict[PydipUnit, set[str]]] = translation.generate_retreats_map(
            self.pydip_players,
            self.pydip_units,
            self.board.provinces,
        )
        self.pydip_commands: list[PydipCommand] = translation.get_commands(
            self.board,
            self.pydip_players,
            self.pydip_units,
            self.retreat_map,
            self.pydip_map,
        )
        self.phase: Phase = self.board.phase

    def adjudicate(self) -> Board:
        # TODO: (ALPHA) update state (ex. unit.province and province.unit), determine pydip results by debug walkthrough
        if phase.is_moves_phase(self.phase):
            result_state: dict[str, dict[PydipUnit, str]] = resolve_turn(self.pydip_map, self.pydip_commands)
        elif phase.is_retreats_phase(self.phase):
            result_state = resolve_retreats(self.pydip_map, self.pydip_commands)
        elif phase.is_adjustments_phase(self.phase):
            ownership_map = translation.get_ownership_map(self.pydip_map, self.board)
            adjustment_counts = translation.get_adjustment_counts(self.board)
            result_state = resolve_adjustment(ownership_map, adjustment_counts, self.pydip_units, self.pydip_commands)
        else:
            raise ValueError(f"Illegal phase: {self.phase.name}")

        raise RuntimeError("Adjudication has not yet been fully implemented.")
