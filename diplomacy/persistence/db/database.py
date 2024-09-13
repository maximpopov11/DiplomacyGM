import logging
import sqlite3

from diplomacy.map_parser.vector.config_svg import SVG_PATH
from diplomacy.map_parser.vector.vector import Parser
from diplomacy.persistence.board import Board
from diplomacy.persistence.order import (
    Core,
    Hold,
    ConvoyMove,
    Move,
    Support,
    ConvoyTransport,
    RetreatDisband,
    RetreatMove,
)
from diplomacy.persistence.phase import phases
from diplomacy.persistence.province import Province
from diplomacy.persistence.unit import UnitType, Unit

logger = logging.getLogger(__name__)

SQL_FILE_PATH = "bot_db.sqlite"


class _DatabaseConnection:
    def __init__(self, db_file: str = SQL_FILE_PATH):
        try:
            self._connection = sqlite3.connect(db_file)
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
        logger.info(f"Loading {len(board_data)} boards from DB")
        boards = dict()
        for board_row in board_data:
            board_id, phase_string, svg_file = board_row

            # TODO - THIS WILL BREAK EVERYTHING ONCE WE HIT WINTER!!
            #  we need to add year into phases. This is a temporary solution.
            phase = next(phase for phase in phases if phase.name == phase_string)
            if (board_id, phase.next.name, svg_file) in board_data:
                continue

            logger.info(f"Loading board with ID {board_id}")

            # TODO - we should eventually store things like coords, adjacencies, etc
            #  so we don't have to reparse the whole board each time
            board = Parser().parse()
            board.phase = next(phase for phase in phases if phase.name == phase_string)
            board.board_id = board_id

            player_data = cursor.execute(
                "SELECT player_name, color FROM players WHERE board_id=?", (board_id,)
            ).fetchall()
            player_info_by_name = {player_name: color for player_name, color in player_data}
            for player in board.players:
                if player.name not in player_info_by_name:
                    logger.warning(f"Couldn't find player {player.name} in DB")
                    continue
                color = player_info_by_name[player.name]
                player.color = color
                player.units = set()
                player.centers = set()
                # TODO - player build orders

            province_data = cursor.execute(
                "SELECT province_name, owner, core, half_core FROM provinces WHERE board_id=? and phase=?",
                (board_id, phase_string),
            ).fetchall()
            province_info_by_name = {
                province_name: (owner, core, half_core) for province_name, owner, core, half_core in province_data
            }
            unit_data = cursor.execute(
                "SELECT location, is_dislodged, owner, is_army, order_type, order_destination, order_source FROM units WHERE board_id=? and phase=?",
                (board_id, phase_string),
            ).fetchall()

            for province in board.provinces:
                if province.name not in province_info_by_name:
                    logger.warning(f"Couldn't find province {province.name} in DB")
                else:
                    owner, core, half_core = province_info_by_name[province.name]

                    if owner is not None:
                        owner_player = board.get_player(owner)
                        province.owner = owner_player

                        if province.has_supply_center:
                            owner_player.centers.add(province)
                    else:
                        province.owner = None

                    core_player = None
                    if core is not None:
                        core_player = board.get_player(core)
                    province.core = core_player

                    half_core_player = None
                    if half_core is not None:
                        half_core_player = board.get_player(half_core)
                    province.half_core = half_core_player
                    province.unit = None
                    province.dislodged_unit = None

            board.units.clear()
            for unit_info in unit_data:
                location, is_dislodged, owner, is_army, order_type, order_destination, order_source = unit_info
                province, coast = board.get_province_and_coast(location)
                owner_player = board.get_player(owner)
                unit = Unit(UnitType.ARMY if is_army else UnitType.FLEET, owner_player, province, coast, None)
                if is_dislodged:
                    province.dislodged_unit = unit
                else:
                    province.unit = unit
                owner_player.units.add(unit)
                board.units.add(unit)
            # AAAAA We shouldn't be having to loop twice; why is ComplexOrder.source a Unit? Turn it into a province or something
            # Currently we have to loop twice because it's a unit and we need to have all the units set up before parsing orders because of it
            for unit_info in unit_data:
                location, is_dislodged, owner, is_army, order_type, order_destination, order_source = unit_info
                if order_type is not None:
                    order_classes = [
                        Hold,
                        Core,
                        Move,
                        ConvoyMove,
                        ConvoyTransport,
                        Support,
                        RetreatMove,
                        RetreatDisband,
                    ]
                    order_class = next(_class for _class in order_classes if _class.__name__ == order_type)
                    destination_province = None
                    if order_destination is not None:
                        destination_province, destination_coast = board.get_province_and_coast(order_destination)
                        if destination_coast is not None:
                            destination_province = destination_coast
                    source_unit = None
                    if order_source is not None:
                        source_province, source_coast = board.get_province_and_coast(order_source)
                        if source_coast is not None:
                            source_province = source_coast
                        source_unit = source_province.unit
                    if order_class in [Hold, Core, RetreatDisband]:
                        order = order_class()
                    elif order_class in [Move, ConvoyMove, RetreatMove]:
                        order = order_class(destination=destination_province)
                    elif order_class in [Support, ConvoyTransport]:
                        order = order_class(destination=destination_province, source=source_unit)
                    else:
                        raise ValueError(f"Could not parse {order_class}")

                    province, coast = board.get_province_and_coast(location)
                    if is_dislodged:
                        province.dislodged_unit.order = order
                    else:
                        province.unit.order = order

            boards[board_id] = board

        cursor.close()
        logger.info("Successfully loaded")
        return boards

    def save_board(self, board_id: int, board: Board):
        # TODO: Check if board already exists
        cursor = self._connection.cursor()
        cursor.execute(
            "INSERT INTO boards (board_id, phase, map_file) VALUES (?, ?, ?);", (board_id, board.phase.name, SVG_PATH)
        )
        cursor.executemany(
            "INSERT INTO players (board_id, player_name, color) VALUES (?, ?, ?)",
            [(board_id, player.name, player.color) for player in board.players],
        )
        cursor.executemany(
            "INSERT INTO provinces (board_id, phase, province_name, owner, core, half_core) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    board_id,
                    board.phase.name,
                    province.name,
                    province.owner.name if province.owner else None,
                    province.core.name if province.core else None,
                    province.half_core.name if province.half_core else None,
                )
                for province in board.provinces
            ],
        )
        # TODO - this is hacky
        cursor.executemany(
            "INSERT INTO units (board_id, phase, location, is_dislodged, owner, is_army, order_type, order_destination, order_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    board_id,
                    board.phase.name,
                    unit.get_location().name,
                    unit == unit.province.dislodged_unit,
                    unit.player.name,
                    unit.unit_type == UnitType.ARMY,
                    unit.order.__class__.__name__ if unit.order is not None else None,
                    getattr(getattr(unit.order, "destination"), "name") if unit.order is not None else None,
                    getattr(getattr(unit.order, "source"), "name") if unit.order is not None else None,
                )
                for unit in board.units
            ],
        )
        cursor.close()
        self._connection.commit()

    def save_order_for_units(self, board_id: int, phase_name: str, units: list[Unit]):
        cursor = self._connection.cursor()
        cursor.executemany(
            "UPDATE units SET order_type=?, order_destination=?, order_source=? WHERE board_id=? and phase=? and location=? and is_dislodged=?",
            [
                (
                    unit.order.__class__.__name__ if unit.order is not None else None,
                    getattr(getattr(unit.order, "destination", None), "name", None) if unit.order is not None else None,
                    (
                        getattr(getattr(getattr(unit.order, "source", None), "province", None), "name", None)
                        if unit.order is not None
                        else None
                    ),
                    board_id,
                    phase_name,
                    unit.get_location().name,
                    unit.province.dislodged_unit == unit,
                )
                for unit in units
            ],
        )
        cursor.close()
        self._connection.commit()

    def execute_arbitrary_sql(self, sql: str, args: tuple):
        cursor = self._connection.cursor()
        cursor.execute(sql, args)
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
