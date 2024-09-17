import logging

from diplomacy.custom_adjudicator.adjudicator import make_adjudicator
from diplomacy.custom_adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.vector import oneTrueParser
from diplomacy.persistence.board import Board
from diplomacy.persistence.db import database
from diplomacy.persistence.phase import phases
from diplomacy.persistence.player import Player

logger = logging.getLogger(__name__)

# TODO: (DB) variants table that holds starting state & map: insert parsed Imp Dip for now
# TODO: (DB) games table (copy of a variant data, has server ID)


class Manager:
    """Manager acts as an intermediary between Bot (the Discord API), Board (the board state), the database."""

    def __init__(self):
        self._database = database.get_connection()
        self._boards: dict[int, Board] = self._database.get_boards()
        # TODO: have multiple for each variant?
        # do it like this so that the parser can cache data between board initilizations

    def list_servers(self) -> set[int]:
        return set(self._boards.keys())

    def create_game(self, server_id: int) -> str:
        if self._boards.get(server_id):
            raise RuntimeError("A game already exists in this server.")

        logger.info(f"Creating new [ImpDip] game in server {server_id}")
        # TODO: (DB) get board from variant DB
        self._boards[server_id] = oneTrueParser.parse()
        self._boards[server_id].board_id = server_id
        self._database.save_board(server_id, self._boards[server_id])

        # TODO: (DB) return map state
        return "ImpDip game created"

    def get_board(self, server_id: int) -> Board:
        board = self._boards.get(server_id)
        if not board:
            raise RuntimeError("There is no existing game this this server.")
        return board

    def draw_moves_map(self, server_id: int, player_restriction: Player | None) -> str:
        return Mapper(self._boards[server_id]).draw_moves_map(self._boards[server_id].phase, player_restriction)

    def adjudicate(self, server_id: int) -> str:
        # mapper = Mapper(self._boards[server_id])
        # mapper.draw_moves_map(None)
        adjudicator = make_adjudicator(self._boards[server_id])
        # TODO - use adjudicator.orders() (tells you which ones succeeded and failed) to draw a better moves map
        new_board = adjudicator.run()
        new_board.phase = new_board.phase.next
        if new_board.phase.name == "Spring Moves":
            new_board.year += 1
        logger.info("Adjudicator ran successfully")
        self._boards[server_id] = new_board
        self._database.save_board(server_id, new_board)
        mapper = Mapper(new_board)
        return mapper.draw_current_map()
        # TODO: (DB) update board, moves map, results map at server id at turn in db
        # TODO: (DB) when updating board, update SVG so it can be reread if needed
        # TODO: (DB) protect against malicious inputs (ex. orders) like drop table
        #  - this is all good
        # TODO: (DB) return both moves and results map

    def rollback(self, server_id: int) -> tuple[str, str]:
        logger.info(f"Rolling back in server {server_id}")
        board = self._boards[server_id]
        last_phase = next(phase for phase in phases if phase.next == board.phase)
        last_phase_year = board.year
        if board.phase.name == "Spring Moves":
            last_phase_year -= 1

        old_board = self._database.get_board(board.board_id, last_phase, last_phase_year)
        if old_board is None:
            raise ValueError(f"There is no {last_phase_year} {last_phase.name} board for this server")

        self._database.delete_board(board)
        self._boards[server_id] = old_board
        mapper = Mapper(old_board)
        return f"Rolled back to {old_board.get_phase_and_year_string()}", mapper.draw_current_map()

    def reload(self, server_id: int) -> tuple[str, str]:
        logger.info(f"Reloading server {server_id}")
        board = self._boards[server_id]

        loaded_board = self._database.get_board(server_id, board.phase, board.year)
        if loaded_board is None:
            raise ValueError(f"There is no {board.year} {board.phase.name} board for this server")

        self._boards[server_id] = loaded_board
        mapper = Mapper(loaded_board)
        return f"Reloaded board for phase {loaded_board.get_phase_and_year_string()}", mapper.draw_current_map()
