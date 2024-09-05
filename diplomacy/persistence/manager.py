from diplomacy.adjudicator.adjudicator import Adjudicator
from diplomacy.adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.vector import Parser
from diplomacy.persistence.board import Board
from diplomacy.persistence.player import Player


# TODO: (DB) variants table that holds starting state & map: insert parsed Imp Dip for now
# TODO: (DB) games table (copy of a variant data, has server ID)


class Manager:
    """Manager acts as an intermediary between Bot (the Discord API), Board (the board state), the database."""

    def __init__(self):
        self._boards: dict[int, Board] = {}

    def create_game(self, server_id: int) -> str:
        if self._boards[server_id]:
            raise RuntimeError("A game already exists in this server.")

        # TODO: (DB) get board from variant DB
        self._boards[server_id] = Parser().parse()

        # TODO: (DB) return map state
        raise RuntimeError("Game creation has not yet been implemented.")

    def get_board(self, server_id: int) -> Board:
        board = self._boards[server_id]
        if not board:
            raise RuntimeError("There is no existing game this this server.")
        return board

    def draw_moves_map(self, server_id: int, player_restriction: Player | None) -> None:
        Mapper(self._boards[server_id]).draw_moves_map(player_restriction)

    def adjudicate(self, server_id: int) -> None:
        board = Adjudicator(self._boards[server_id]).adjudicate()
        self._boards[server_id] = board
        mapper = Mapper(board)
        mapper.draw_moves_map(
            None
        )  # FIXME: you should draw moves on the previous 'board', get results from the new one
        mapper.draw_current_map()
        # TODO: (DB) update board, moves map, results map at server id at turn in db
        # TODO: (DB) when updating board, update SVG so it can be reread if needed
        # TODO: (DB) protect against malicious inputs (ex. orders) like drop table
        # TODO: (DB) return both moves and results map

    def rollback(self) -> str:
        # TODO: (DB) get former turn board & moves map & results map from DB; update board; return maps
        raise RuntimeError("Rollback not yet implemented.")
