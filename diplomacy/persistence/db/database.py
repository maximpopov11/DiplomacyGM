import sqlite3
import logging

from diplomacy.map_parser.vector.config_svg import SVG_PATH
from diplomacy.map_parser.vector.vector import Parser
from diplomacy.persistence.board import Board
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType

logger = logging.getLogger(__name__)

SQL_FILE_PATH = "bot_db.sqlite"


class _DatabaseConnection:
    def __init__(self):
        try:
            self._connection = sqlite3.connect(SQL_FILE_PATH)
            logger.info("Connection to SQLite DB successful")
        except IOError as ex:
            logger.error("Could not open SQLite DB", exc_info=ex)
            self._connection = sqlite3.connect(":memory:")  # Special wildcard; in-memory db

        self._initialize_schema()

    def _initialize_schema(self):
        # FIXME: move the sql file somewhere more accessible (maybe it shouldn't be inside the package? /resources ?)
        with open("diplomacy/persistence/db/schema.sql", "r") as sql_file:
            cursor = self._connection.cursor()
            cursor.executescript(sql_file.read())
            cursor.close()

    def get_boards(self) -> dict[int, Board]:
        cursor = self._connection.cursor()
        board_data = cursor.execute("SELECT * FROM boards").fetchall()
        for board_row in board_data:
            board_id, svg_file, phase_string = board_row

            player_data = cursor.execute(
                "SELECT player_name, username, color FROM players WHERE board_id=?", (board_id,)
            ).fetchall()
            # TODO: add username to Player constructor, so we can pass it in too
            players = {Player(player_name, color, set(), set()) for player_name, username, color in player_data}

            # TODO: finish this
            pass

        cursor.close()
        return dict()

    def save_board(self, board_id: int, board: Board):
        # TODO: Check if board already exists
        cursor = self._connection.cursor()
        cursor.execute(
            "INSERT INTO boards (board_id, map_file, phase) VALUES (?, ?, ?);", (board_id, SVG_PATH, board.phase.name)
        )
        cursor.executemany(
            "INSERT INTO players (board_id, player_name, username, color) VALUES (?, ?, ?, ?)",
            [(board_id, player.name, player.username, player.color) for player in board.players],
        )
        cursor.executemany(
            "INSERT INTO provinces (board_id, province_name, owner, core, half_core) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    board_id,
                    province.name,
                    province.owner.name if province.owner else None,
                    province.core.name if province.core else None,
                    province.half_core.name if province.half_core else None,
                )
                for province in board.provinces
            ],
        )
        cursor.executemany(
            "INSERT INTO units (board_id, location, is_dislodged, owner, is_army) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    board_id,
                    unit.province.name,
                    unit == unit.province.dislodged_unit,
                    unit.player.name,
                    unit.unit_type == UnitType.ARMY,
                )
                for unit in board.units
            ],
        )
        cursor.close()
        self._connection.commit()

    def __del__(self):
        self._connection.commit()
        self._connection.close()


_db_class: _DatabaseConnection | None = None


def get_connection() -> _DatabaseConnection:
    global _db_class
    if _db_class:
        return _db_class
    _db_class = _DatabaseConnection()
    return _db_class
