import logging
import time

from diplomacy.adjudicator.adjudicator import make_adjudicator
from diplomacy.adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.vector import get_parser
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.db import database
from diplomacy.persistence.player import Player
from diplomacy.persistence.spec_request import SpecRequest

logger = logging.getLogger(__name__)


class Manager:
    """Manager acts as an intermediary between Bot (the Discord API), Board (the board state), the database."""

    def __init__(self):
        self._database = database.get_connection()
        self._boards: dict[int, Board] = self._database.get_boards()
        self._spec_requests: dict[int, list[SpecRequest]] = (
            self._database.get_spec_requests()
        )
        # TODO: have multiple for each variant?
        # do it like this so that the parser can cache data between board initilizations

    def list_servers(self) -> set[int]:
        return set(self._boards.keys())

    def create_game(self, server_id: int, gametype: str = "impdip.json") -> str:
        if self._boards.get(server_id):
            raise RuntimeError("A game already exists in this server.")

        logger.info(f"Creating new game in server {server_id}")
        self._boards[server_id] = get_parser(gametype).parse()
        self._boards[server_id].board_id = server_id
        self._database.save_board(server_id, self._boards[server_id])

        return f"{self._boards[server_id].data['name']} game created"

    def get_spec_request(self, server_id: int, user_id: int) -> SpecRequest | None:
        if server_id not in self._spec_requests:
            return None

        for req in self._spec_requests[server_id]:
            if req.user_id == user_id:
                return req

        return None

    def save_spec_request(self, server_id: int, user_id: int, role_id: int) -> str:
        # create new list if first time in server
        if server_id not in self._spec_requests:
            self._spec_requests[server_id] = []

        obj = SpecRequest(server_id, user_id, role_id)

        if self.get_spec_request(server_id, user_id):
            return "User has already been accepted for a request in this Server."

        self._spec_requests[server_id].append(obj)
        self._database.save_spec_request(obj)

        return f"Approved request Logged!"

    def get_board(self, server_id: int) -> Board:
        board = self._boards.get(server_id)
        if not board:
            raise RuntimeError("There is no existing game this this server.")
        return board

    def total_delete(self, server_id: int):
        self._database.total_delete(self._boards[server_id])
        del self._boards[server_id]

    def draw_moves_map(
        self,
        server_id: int,
        player_restriction: Player | None,
        color_mode: str | None = None,
        turn: tuple[str, phase] | None = None
    ) -> tuple[str, str]:
        start = time.time()

        cur_board = self._boards[server_id]
        if turn is None:
            board = cur_board
            season = board.phase
        else:
            board = self._database.get_board(
                cur_board.board_id, turn[1], int(turn[0]) - cur_board.year_offset, cur_board.fish, cur_board.datafile
            )
            if board is None:
                raise RuntimeError(
                    f"There is no {turn[1].name} {turn[0]} board for this server"
                )
            season = turn[1]
            if (board.year < cur_board.year
                or board.year == cur_board.year and season.index < cur_board.phase.index):
                player_restriction = None
        svg, file_name = Mapper(
            board, color_mode=color_mode
        ).draw_moves_map(season, player_restriction)

        elapsed = time.time() - start
        logger.info(f"manager.draw_moves_map.{server_id}.{elapsed}s")
        return svg, file_name

    def adjudicate(self, server_id: int) -> None:
        start = time.time()

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

        elapsed = time.time() - start
        logger.info(f"manager.adjudicate.{server_id}.{elapsed}s")

    def draw_fow_current_map(
        self,
        server_id: int,
        player_restriction: Player | None,
        color_mode: str | None = None,
    ) -> tuple[str, str]:
        start = time.time()

        svg, file_name = Mapper(
            self._boards[server_id], player_restriction, color_mode
        ).draw_current_map()

        elapsed = time.time() - start
        logger.info(f"manager.draw_fow_current_map.{server_id}.{elapsed}s")
        return svg, file_name

    def draw_current_map(
        self,
        server_id: int,
        color_mode: str | None = None,
        turn: tuple[str, phase] | None = None
    ) -> tuple[str, str]:
        start = time.time()
        
        cur_board = self._boards[server_id]
        if turn is None:
            board = cur_board
            season = board.phase
        else:
            board = self._database.get_board(
                cur_board.board_id, turn[1], int(turn[0]) - 1642, cur_board.fish, cur_board.datafile
            )
            if board is None:
                raise RuntimeError(
                    f"There is no {turn[1].name} {turn[0]} board for this server"
                )
            season = turn[1]
        svg, file_name = Mapper(
            board, color_mode=color_mode
        ).draw_current_map()

        elapsed = time.time() - start
        logger.info(f"manager.draw_current_map.{server_id}.{elapsed}s")
        return svg, file_name

    def draw_fow_players_moves_map(
        self,
        server_id: int,
        player_restriction: Player | None,
        color_mode: str | None = None,
    ) -> tuple[str, str]:
        start = time.time()

        if player_restriction:
            svg, file_name = Mapper(
                self._boards[server_id], player_restriction, color_mode=color_mode
            ).draw_moves_map(self._boards[server_id].phase, player_restriction)
        else:
            svg, file_name = Mapper(self._boards[server_id], None).draw_moves_map(
                self._boards[server_id].phase, None
            )

        elapsed = time.time() - start
        logger.info(f"manager.draw_fow_players_moves_map.{server_id}.{elapsed}s")
        return svg, file_name

    def draw_fow_moves_map(
        self, server_id: int, player_restriction: Player | None
    ) -> tuple[str, str]:
        start = time.time()

        svg, file_name = Mapper(
            self._boards[server_id], player_restriction
        ).draw_moves_map(self._boards[server_id].phase, None)

        elapsed = time.time() - start
        logger.info(f"manager.draw_fow_moves_map.{server_id}.{elapsed}s")
        return svg, file_name

    def draw_fow_gui_map(
        self,
        server_id: int,
        player_restriction: Player | None,
        color_mode: str | None = None,
    ) -> tuple[str, str]:
        start = time.time()

        svg, file_name = Mapper(
            self._boards[server_id], player_restriction, color_mode=color_mode
        ).draw_gui_map(self._boards[server_id].phase, None)

        elapsed = time.time() - start
        logger.info(f"manager.draw_fow_moves_map.{server_id}.{elapsed}s")
        return svg, file_name

    def draw_gui_map(
        self,
        server_id: int,
        player_restriction: Player | None,
        color_mode: str | None = None,
    ) -> tuple[str, str]:
        start = time.time()

        svg, file_name = Mapper(
            self._boards[server_id], color_mode=color_mode
        ).draw_gui_map(self._boards[server_id].phase, player_restriction)

        elapsed = time.time() - start
        logger.info(f"manager.draw_moves_map.{server_id}.{elapsed}s")
        return svg, file_name

    def rollback(self, server_id: int) -> dict[str, ...]:
        logger.info(f"Rolling back in server {server_id}")
        board = self._boards[server_id]
        # TODO: what happens if we're on the first phase?
        last_phase = board.phase.previous
        last_phase_year = board.year
        if board.phase.name == "Spring Moves":
            last_phase_year -= 1

        old_board = self._database.get_board(
            board.board_id, last_phase, last_phase_year, board.fish, board.datafile
        )
        if old_board is None:
            raise ValueError(
                f"There is no {last_phase_year} {last_phase.name} board for this server"
            )

        self._database.delete_board(board)
        self._boards[server_id] = old_board
        mapper = Mapper(old_board)

        message = f"Rolled back to {old_board.get_phase_and_year_string()}"
        file, file_name = mapper.draw_current_map()
        return {"message": message, "file": file, "file_name": file_name}

    def get_previous_board(self, server_id: int) -> Board | None:
        board = self._boards[server_id]
        # TODO: what happens if we're on the first phase?
        last_phase = board.phase.previous
        last_phase_year = board.year
        if board.phase.name == "Spring Moves":
            last_phase_year -= 1
        old_board = self._database.get_board(
            board.board_id, last_phase, last_phase_year, board.fish, board.datafile
        )
        return old_board

    def reload(self, server_id: int) -> dict[str, ...]:
        logger.info(f"Reloading server {server_id}")
        board = self._boards[server_id]

        loaded_board = self._database.get_board(
            server_id, board.phase, board.year, board.fish, board.datafile
        )
        if loaded_board is None:
            raise ValueError(
                f"There is no {board.year} {board.phase.name} board for this server"
            )

        self._boards[server_id] = loaded_board
        mapper = Mapper(loaded_board)

        message = f"Reloaded board for phase {loaded_board.get_phase_and_year_string()}"
        file, file_name = mapper.draw_current_map()
        return {"message": message, "file": file, "file_name": file_name}
