import logging
import sqlite3
from collections.abc import Iterable

# TODO: Find a better way to do this
# maybe use a copy from manager?
from diplomacy.map_parser.vector.vector import get_parser
from diplomacy.persistence import phase
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
    Build,
    Disband,
)
from diplomacy.persistence.player import Player
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
        board_keys = [(row[0], row[1]) for row in board_data]
        logger.info(f"Loading {len(board_data)} boards from DB")
        boards = dict()
        for board_row in board_data:
            board_id, phase_string, data_file, fish = board_row

            split_index = phase_string.index(" ")
            year = int(phase_string[:split_index])
            phase_name = phase_string[split_index:].strip()
            current_phase = phase.get(phase_name)
            next_phase = current_phase.next
            next_phase_year = year
            if next_phase.name == "Spring Moves":
                next_phase_year += 1
            if (board_id, f"{next_phase_year} {next_phase.name}") in board_keys:
                continue

            if fish is None:
                fish = 0

            board = self._get_board(data_file, board_id, current_phase, year, fish, cursor)

            boards[board_id] = board

        cursor.close()
        logger.info("Successfully loaded")
        return boards

    def get_board(self, board_id: int, board_phase: phase.Phase, year: int, fish: int) -> Board | None:
        cursor = self._connection.cursor()

        board_data = cursor.execute(
            "SELECT * FROM boards WHERE board_id=? and phase=?", (board_id, f"{year} {board_phase.name}")
        ).fetchone()
        if not board_data:
            cursor.close()
            return None

        board = self._get_board(board_id, board_phase, year, fish, cursor)
        cursor.close()
        return board

    def _get_board(self, data_file: str, board_id: int, board_phase: phase.Phase, year: int, fish: int, cursor) -> Board:
        logger.info(f"Loading board with ID {board_id}")
        # TODO - we should eventually store things like coords, adjacencies, etc
        #  so we don't have to reparse the whole board each time
        board = get_parser(data_file).parse()
        board.phase = board_phase
        board.year = year
        board.fish = fish
        board.board_id = board_id

        player_data = cursor.execute("SELECT player_name, color FROM players WHERE board_id=?", (board_id,)).fetchall()
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
        if phase.is_builds(board_phase):
            builds_data = cursor.execute(
                "SELECT player, location, is_build, is_army FROM builds WHERE board_id=? and phase=?",
                (board_id, board.get_phase_and_year_string()),
            ).fetchall()
            player_by_name = {player.name: player for player in board.players}
            for player_name, location, is_build, is_army in builds_data:
                if player_name not in player_by_name:
                    logger.warning(f"Unknown player: {player_name}")
                    continue
                player = player_by_name[player_name]
                if is_build:
                    player_order = Build(board.get_location(location), UnitType.ARMY if is_army else UnitType.FLEET)
                else:
                    player_order = Disband(board.get_location(location))
                player.build_orders.add(player_order)

        province_data = cursor.execute(
            "SELECT province_name, owner, core, half_core FROM provinces WHERE board_id=? and phase=?",
            (board_id, board.get_phase_and_year_string()),
        ).fetchall()
        province_info_by_name = {
            province_name: (owner, core, half_core) for province_name, owner, core, half_core in province_data
        }
        unit_data = cursor.execute(
            "SELECT location, is_dislodged, owner, is_army, order_type, order_destination, order_source FROM units WHERE board_id=? and phase=?",
            (board_id, board.get_phase_and_year_string()),
        ).fetchall()
        for province in board.provinces:
            if province.name not in province_info_by_name:
                logger.warning(f"Couldn't find province {province.name} in DB")
                continue

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
            if is_dislodged:
                retreat_ops = cursor.execute(
                    "SELECT retreat_loc FROM retreat_options WHERE board_id=? and phase=? and origin=?",
                    (board_id, board.get_phase_and_year_string(), location),
                )
                retreat_options = set(map(board.get_location, set().union(*retreat_ops)))
            else:
                retreat_options = None
            unit = Unit(UnitType.ARMY if is_army else UnitType.FLEET, owner_player, province, coast, retreat_options)
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

        return board

    def save_board(self, board_id: int, board: Board):
        # TODO: Check if board already exists
        cursor = self._connection.cursor()
        cursor.execute(
            "INSERT INTO boards (board_id, phase, data_file, fish) VALUES (?, ?, ?, ?);",
            (board_id, board.get_phase_and_year_string(), board.datafile, board.fish),
        )
        cursor.executemany(
            "INSERT INTO players (board_id, player_name, color) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            [(board_id, player.name, player.color) for player in board.players],
        )

        # cache = []
        # for p in board.provinces:
        #     if p.name == "NICE":
        #         print(p.type)
        #         import matplotlib.pyplot as plt
        #         import shapely
        #         if isinstance(p.geometry, shapely.Polygon):
        #             plt.plot(*p.geometry.exterior.xy)
        #         else:
        #             for geo in p.geometry.geoms:
        #                 plt.plot(*geo.exterior.xy)
        # plt.gca().invert_yaxis()
        # plt.show()
        print(board_id, board.get_phase_and_year_string())


        cursor.executemany(
            "INSERT INTO provinces (board_id, phase, province_name, owner, core, half_core) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    board_id,
                    board.get_phase_and_year_string(),
                    province.name,
                    province.owner.name if province.owner else None,
                    province.core.name if province.core else None,
                    province.half_core.name if province.half_core else None,
                )
                for province in board.provinces
            ],
        )
        cursor.executemany(
            "INSERT INTO builds (board_id, phase, player, location, is_build, is_army) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    board_id,
                    board.get_phase_and_year_string(),
                    player.name,
                    build_order.location.name,
                    isinstance(build_order, Build),
                    getattr(build_order, "unit_type", None) == UnitType.ARMY,
                )
                for player in board.players
                for build_order in player.build_orders
            ],
        )
        # TODO - this is hacky
        cursor.executemany(
            "INSERT INTO units (board_id, phase, location, is_dislodged, owner, is_army, order_type, order_destination, order_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    board_id,
                    board.get_phase_and_year_string(),
                    unit.location().name,
                    unit == unit.province.dislodged_unit,
                    unit.player.name,
                    unit.unit_type == UnitType.ARMY,
                    unit.order.__class__.__name__ if unit.order is not None else None,
                    getattr(getattr(unit.order, "destination", None), "name", None) if unit.order is not None else None,
                    (
                        getattr(getattr(getattr(unit.order, "source", None), "province", None), "name", None)
                        if unit.order is not None
                        else None
                    ),
                )
                for unit in board.units
            ],
        )
        cursor.executemany(
            "INSERT INTO retreat_options (board_id, phase, origin, retreat_loc) VALUES (?, ?, ?, ?)",
            [
                (board_id, board.get_phase_and_year_string(), unit.location().name, retreat_option.name)
                for unit in board.units
                if unit.retreat_options is not None
                for retreat_option in unit.retreat_options
            ],
        )
        cursor.close()
        self._connection.commit()

    def save_order_for_units(self, board: Board, units: Iterable[Unit]):
        cursor = self._connection.cursor()
        cursor.executemany(
            "UPDATE units SET order_type=?, order_destination=?, order_source=? "
            "WHERE board_id=? and phase=? and location=? and is_dislodged=?",
            [
                (
                    unit.order.__class__.__name__ if unit.order is not None else None,
                    getattr(getattr(unit.order, "destination", None), "name", None) if unit.order is not None else None,
                    (
                        getattr(getattr(getattr(unit.order, "source", None), "province", None), "name", None)
                        if unit.order is not None
                        else None
                    ),
                    board.board_id,
                    board.get_phase_and_year_string(),
                    unit.location().name,
                    unit.province.dislodged_unit == unit,
                )
                for unit in units
            ],
        )
        cursor.executemany(
            "DELETE FROM retreat_options WHERE board_id=? and phase=? and origin=?",
            [
                (board.board_id, board.get_phase_and_year_string(), unit.location().name)
                for unit in units
                if unit.retreat_options is not None
            ],
        )
        cursor.executemany(
            "INSERT INTO retreat_options (board_id, phase, origin, retreat_loc) VALUES (?, ?, ?, ?)",
            [
                (board.board_id, board.get_phase_and_year_string(), unit.location().name, retreat_option.name)
                for unit in units
                if unit.retreat_options is not None
                for retreat_option in unit.retreat_options
            ],
        )
        cursor.close()
        self._connection.commit()

    def save_build_orders_for_players(self, board: Board, player: Player | None):
        if player is None:
            players = board.players
        else:
            players = {player}
        cursor = self._connection.cursor()
        cursor.executemany(
            "INSERT INTO builds (board_id, phase, player, location, is_build, is_army) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (board_id, phase, player, location) DO UPDATE SET is_build=?, is_army=?",
            [
                (
                    board.board_id,
                    board.get_phase_and_year_string(),
                    player.name,
                    build_order.location.name,
                    isinstance(build_order, Build),
                    getattr(build_order, "unit_type", None) == UnitType.ARMY,
                    isinstance(build_order, Build),
                    getattr(build_order, "unit_type", None) == UnitType.ARMY,
                )
                for player in players
                for build_order in player.build_orders
            ],
        )
        cursor.close()
        self._connection.commit()

    def delete_board(self, board: Board):
        cursor = self._connection.cursor()
        cursor.execute(
            "DELETE FROM boards WHERE board_id=? AND phase=?", (board.board_id, board.get_phase_and_year_string())
        )
        cursor.execute(
            "DELETE FROM provinces WHERE board_id=? AND phase=?", (board.board_id, board.get_phase_and_year_string())
        )
        cursor.execute(
            "DELETE FROM units WHERE board_id=? AND phase=?", (board.board_id, board.get_phase_and_year_string())
        )
        cursor.execute(
            "DELETE FROM builds WHERE board_id=? AND phase=?", (board.board_id, board.get_phase_and_year_string())
        )
        cursor.execute(
            "DELETE FROM retreat_options WHERE board_id=? AND phase=?",
            (board.board_id, board.get_phase_and_year_string()),
        )
        cursor.close()
        self._connection.commit()

    def execute_arbitrary_sql(self, sql: str, args: tuple):
        # TODO - everywhere using this should just be made into a method probably? idk
        cursor = self._connection.cursor()
        cursor.execute(sql, args)
        cursor.close()
        self._connection.commit()

    def executemany_arbitrary_sql(self, sql: str, args: list[tuple]):
        cursor = self._connection.cursor()
        cursor.executemany(sql, args)
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
