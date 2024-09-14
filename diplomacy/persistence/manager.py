import logging

from diplomacy.custom_adjudicator.adjudicator import Adjudicator
from diplomacy.custom_adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.vector import Parser
from diplomacy.persistence.board import Board
from diplomacy.persistence.db import database
from diplomacy.persistence.player import Player

logger = logging.getLogger(__name__)

# TODO: (DB) variants table that holds starting state & map: insert parsed Imp Dip for now
# TODO: (DB) games table (copy of a variant data, has server ID)


class Manager:
    """Manager acts as an intermediary between Bot (the Discord API), Board (the board state), the database."""

    def __init__(self):
        self._database = database.get_connection()
        self._boards = self._database.get_boards()

    def create_game(self, server_id: int) -> str:
        if self._boards.get(server_id):
            raise RuntimeError("A game already exists in this server.")

        logger.info(f"Creating new [ImpDip] game in server {server_id}")
        # TODO: (DB) get board from variant DB
        self._boards[server_id] = Parser().parse()
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
        return Mapper(self._boards[server_id]).draw_moves_map(player_restriction)

    def adjudicate(self, server_id: int) -> str:
        mapper = Mapper(self._boards[server_id])
        # mapper.draw_moves_map(None)
        adjudicator = Adjudicator(self._boards[server_id])
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

    def rollback(self) -> str:
        # TODO: (!) get former turn board & moves map & results map from DB; update board; return maps
        raise RuntimeError("Rollback not yet implemented.")
