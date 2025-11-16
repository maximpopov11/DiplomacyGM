import logging
from os import supports_dir_fd
import sqlite3
from collections.abc import Iterable

# TODO: Find a better way to do this
# maybe use a copy from manager?
from diplomacy.map_parser.vector.vector import get_parser
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.order import (
    Core,
    NMR,
    Hold,
    ConvoyMove,
    Move,
    Support,
    ConvoyTransport,
    RetreatDisband,
    RetreatMove,
    Build,
    Disband,
    Vassal,
    Liege,
    DualMonarchy,
    Disown,
    Defect,
    RebellionMarker,
    RelationshipOrder,
)
from diplomacy.persistence.player import Player
from diplomacy.persistence.spec_request import SpecRequest
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
            self._connection = sqlite3.connect(
                ":memory:"
            )  # Special wildcard; in-memory db

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
            board_id, phase_string, data_file, fish, name = board_row

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

            board = self._get_board(
                board_id, current_phase, year, fish, name, data_file, cursor
            )

            boards[board_id] = board

        cursor.close()
        logger.info("Successfully loaded")
        return boards

    def get_board(
        self,
        board_id: int,
        board_phase: phase.Phase,
        year: int,
        fish: int,
        name: str | None,
        data_file: str,
        clear_status: bool = False,
    ) -> Board | None:
        cursor = self._connection.cursor()

        board_data = cursor.execute(
            "SELECT * FROM boards WHERE board_id=? and phase=?",
            (board_id, f"{year} {board_phase.name}"),
        ).fetchone()
        if not board_data:
            cursor.close()
            return None

        board = self._get_board(board_id, board_phase, year, fish, name, data_file, cursor, clear_status)
        cursor.close()
        return board

    def _get_board(
        self,
        board_id: int,
        board_phase: phase.Phase,
        year: int,
        fish: int,
        name: str | None,
        data_file: str,
        cursor,
        clear_status: bool = False,
    ) -> Board:
        logger.info(f"Loading board with ID {board_id}")
        # TODO - we should eventually store things like coords, adjacencies, etc
        #  so we don't have to reparse the whole board each time
        board = get_parser(data_file).parse()
        board.phase = board_phase
        board.year = year
        board.fish = fish
        board.name = name
        board.board_id = board_id

        player_data = cursor.execute(
            "SELECT player_name, color, liege, points, discord_id FROM players WHERE board_id=?",
            (board_id,),
        ).fetchall()
        player_info_by_name = {
            player_name: (color, liege, points, discord_id)
            for player_name, color, liege, points, discord_id in player_data
        }
        name_to_player = {player.name: player for player in board.players}
        for player in board.players:
            if player.name not in player_info_by_name:
                logger.warning(f"Couldn't find player {player.name} in DB")
                continue
            color, liege, points, discord_id = player_info_by_name[player.name]
            player.render_color = color
            if liege is not None:
                try:
                    player.liege = name_to_player[liege]
                except KeyError:
                    logger.warning(f"Invalid liege of player {player.name}: {liege}")
                player.liege.vassals.append(player)
            if discord_id is not None:
                player.discord_id = discord_id
            player.points = points
            player.units = set()
            player.centers = set()
            # TODO - player build orders
        if phase.is_builds(board_phase):
            builds_data = cursor.execute(
                "SELECT player, location, is_build, is_army FROM builds WHERE board_id=? and phase=?",
                (board_id, board.get_phase_and_year_string()),
            ).fetchall()

            def get_player_by_name(player_name) -> Player | None:
                player_by_name = {player.name: player for player in board.players}

                if player_name not in player_by_name:
                    logger.warning(f"Unknown player: {player_name}")
                    return None

                return player_by_name[player_name]

            for player_name, location, is_build, is_army in builds_data:
                player = get_player_by_name(player_name)

                if player is None:
                    continue

                if is_build:
                    player_order = Build(
                        board.get_location(location),
                        UnitType.ARMY if is_army else UnitType.FLEET,
                    )
                else:
                    player_order = Disband(board.get_location(location))

                player.build_orders.add(player_order)

            vassals_data = cursor.execute(
                "SELECT player, target_player, order_type FROM vassal_orders WHERE board_id=? and phase=?",
                (board_id, board.get_phase_and_year_string()),
            ).fetchall()

            order_classes = [
                Vassal,
                Liege,
                DualMonarchy,
                Disown,
                Defect,
                RebellionMarker,
            ]

            for player_name, target_player_name, order_type in vassals_data:
                player = get_player_by_name(player_name)
                target_player = get_player_by_name(target_player_name)
                order_class = next(
                    order_class
                    for order_class in order_classes
                    if order_class.__name__ == order_type
                )

                order = order_class(target_player)

                player.vassal_orders[target_player] = order

        province_data = cursor.execute(
            "SELECT province_name, owner, core, half_core FROM provinces WHERE board_id=? and phase=?",
            (board_id, board.get_phase_and_year_string()),
        ).fetchall()
        province_info_by_name = {
            province_name: (owner, core, half_core)
            for province_name, owner, core, half_core in province_data
        }
        
        if clear_status:
            cursor.execute("UPDATE units SET failed_order=False WHERE board_id=? and phase=?",
                (board_id, board.get_phase_and_year_string()))
        
        unit_data = cursor.execute(
            "SELECT location, is_dislodged, owner, is_army, order_type, order_destination, order_source, failed_order FROM units WHERE board_id=? and phase=?",
            (board_id, board.get_phase_and_year_string()),
        ).fetchall()
        for province in board.provinces:
            if province.name not in province_info_by_name:
                logger.warning(f"Couldn't find province {province.name} in DB")
                continue

            owner, core, half_core = province_info_by_name[province.name]

            if owner is not None:
                owner_player = board.get_player(owner)
                if owner_player is None:
                    logger.warning(
                        f"Couldn't find corresponding player for {owner} in DB"
                    )
                else:
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
            (
                location,
                is_dislodged,
                owner,
                is_army,
                order_type,
                order_destination,
                order_source,
                hasFailed,
            ) = unit_info
            province, coast = board.get_province_and_coast(location)
            owner_player = board.get_player(owner)
            if is_dislodged:
                retreat_ops = cursor.execute(
                    "SELECT retreat_loc FROM retreat_options WHERE board_id=? and phase=? and origin=?",
                    (board_id, board.get_phase_and_year_string(), location),
                )
                retreat_options = set(
                    map(board.get_location, set().union(*retreat_ops))
                )
            else:
                retreat_options = None
            unit = Unit(
                UnitType.ARMY if is_army else UnitType.FLEET,
                owner_player,
                province,
                coast,
                retreat_options,
            )
            if is_dislodged:
                province.dislodged_unit = unit
            else:
                province.unit = unit
            owner_player.units.add(unit)
            board.units.add(unit)
        # AAAAA We shouldn't be having to loop twice; why is ComplexOrder.source a Unit? Turn it into a province or something
        # Currently we have to loop twice because it's a unit and we need to have all the units set up before parsing orders because of it
        for unit_info in unit_data:
            try:
                (
                    location,
                    is_dislodged,
                    owner,
                    is_army,
                    order_type,
                    order_destination,
                    order_source,
                    hasFailed,
                ) = unit_info
                if order_type is not None:
                    order_classes = [
                        NMR,
                        Hold,
                        Core,
                        Move,
                        ConvoyMove,
                        ConvoyTransport,
                        Support,
                        RetreatMove,
                        RetreatDisband,
                    ]
                    order_class = next(
                        _class
                        for _class in order_classes
                        if _class.__name__ == order_type
                    )
                    destination_province = None
                    if order_destination is not None:
                        destination_province, destination_coast = (
                            board.get_province_and_coast(order_destination)
                        )
                        if destination_coast is not None:
                            destination_province = destination_coast
                    if order_source is not None:
                        source_province, source_coast = board.get_province_and_coast(
                            order_source
                        )
                        if source_coast is not None:
                            source_province = source_coast
                    if order_class == NMR:
                        continue
                    elif order_class in [Hold, Core, RetreatDisband]:
                        order = order_class()
                    elif order_class in [Move, ConvoyMove, RetreatMove]:
                        order = order_class(destination=destination_province)
                    elif order_class in [Support, ConvoyTransport]:
                        order = order_class(
                            destination=destination_province, source=source_province
                        )
                    else:
                        raise ValueError(f"Could not parse {order_class}")
                    
                    order.hasFailed = hasFailed

                    province, coast = board.get_province_and_coast(location)
                    if is_dislodged:
                        province.dislodged_unit.order = order
                    else:
                        province.unit.order = order
            except:
                logger.warning("BAD UNIT INFO: replacing with hold")
                continue
        return board

    def save_board(self, board_id: int, board: Board):
        # TODO: Check if board already exists
        cursor = self._connection.cursor()
        cursor.execute(
            "INSERT INTO boards (board_id, phase, data_file, fish, name) VALUES (?, ?, ?, ?, ?)",
            (board_id, board.get_phase_and_year_string(), board.datafile, board.fish, board.name),
        )
        cursor.executemany(
            "INSERT INTO players (board_id, player_name, color, liege, points) VALUES (?, ?, ?, ?, ?) ON CONFLICT "
            "DO UPDATE SET "
            "color = ?, "
            "liege = ?, "
            "points = ?",
            [
                (
                    board_id,
                    player.name,
                    player.render_color,
                    (None if player.liege is None else str(player.liege)),
                    player.points,
                    player.render_color,
                    (None if player.liege is None else str(player.liege)),
                    player.points,
                )
                for player in board.players
            ],
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

        cache = []
        for p in board.provinces:
            if p.name in cache:
                print(f"{p.name} repeats!!!")
            cache.append(p.name)

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
            "INSERT INTO units (board_id, phase, location, is_dislodged, owner, is_army, order_type, order_destination, order_source, failed_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    board_id,
                    board.get_phase_and_year_string(),
                    unit.location().name,
                    unit == unit.province.dislodged_unit,
                    unit.player.name,
                    unit.unit_type == UnitType.ARMY,
                    unit.order.__class__.__name__ if unit.order is not None else None,
                    (
                        getattr(getattr(unit.order, "destination", None), "name", None)
                        if unit.order is not None
                        else None
                    ),
                    (
                        getattr(
                            getattr(
                                getattr(unit.order, "source", None), "province", None
                            ),
                            "name",
                            None,
                        )
                        if unit.order is not None
                        else None
                    ),
                    unit.order.hasFailed if unit.order is not None else False
                )
                for unit in board.units
            ],
        )
        cursor.executemany(
            "INSERT INTO retreat_options (board_id, phase, origin, retreat_loc) VALUES (?, ?, ?, ?)",
            [
                (
                    board_id,
                    board.get_phase_and_year_string(),
                    unit.location().name,
                    retreat_option.name,
                )
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
            "UPDATE units SET order_type=?, order_destination=?, order_source=?, failed_order=? "
            "WHERE board_id=? and phase=? and location=? and is_dislodged=?",
            [
                (
                    unit.order.__class__.__name__ if unit.order is not None else None,
                    (
                        getattr(getattr(unit.order, "destination", None), "name", None)
                        if unit.order is not None
                        else None
                    ),
                    (
                        getattr(getattr(unit.order, "source", None), "name", None)
                        if unit.order is not None
                        else None
                    ),
                    unit.order.hasFailed if unit.order is not None else False,
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
                (
                    board.board_id,
                    board.get_phase_and_year_string(),
                    unit.location().name,
                )
                for unit in units
                if unit.retreat_options is not None
            ],
        )
        cursor.executemany(
            "INSERT INTO retreat_options (board_id, phase, origin, retreat_loc) VALUES (?, ?, ?, ?)",
            [
                (
                    board.board_id,
                    board.get_phase_and_year_string(),
                    unit.location().name,
                    retreat_option.name,
                )
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
        cursor.executemany(
            "INSERT INTO vassal_orders (board_id, phase, player, target_player, order_type) VALUES (?, ?, ?, ?, ?) ",
            [
                (
                    board.board_id,
                    board.get_phase_and_year_string(),
                    player.name,
                    build_order.player.name,
                    build_order.__class__.__name__,
                )
                for player in players
                for build_order in player.vassal_orders.values()
            ],
        )
        cursor.close()
        self._connection.commit()

    def get_spec_requests(self) -> dict[int, list[SpecRequest]]:
        requests = {}

        cursor = self._connection.cursor()
        request_data = cursor.execute(
            "SELECT server_id, user_id, role_id FROM spec_requests"
        ).fetchall()
        cursor.close()

        for s_id, u_id, r_id in request_data:
            if s_id not in requests:
                requests[s_id] = []

            request = SpecRequest(s_id, u_id, r_id)
            requests[s_id].append(request)

        return requests

    def save_spec_request(self, request: SpecRequest):
        cursor = self._connection.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO spec_requests (server_id, user_id, role_id) VALUES (?, ?, ?)",
            (request.server_id, request.user_id, request.role_id),
        )

        cursor.close()
        self._connection.commit()

    def delete_board(self, board: Board):
        cursor = self._connection.cursor()
        cursor.execute(
            "DELETE FROM boards WHERE board_id=? AND phase=?",
            (board.board_id, board.get_phase_and_year_string()),
        )
        cursor.execute(
            "DELETE FROM provinces WHERE board_id=? AND phase=?",
            (board.board_id, board.get_phase_and_year_string()),
        )
        cursor.execute(
            "DELETE FROM units WHERE board_id=? AND phase=?",
            (board.board_id, board.get_phase_and_year_string()),
        )
        cursor.execute(
            "DELETE FROM builds WHERE board_id=? AND phase=?",
            (board.board_id, board.get_phase_and_year_string()),
        )
        cursor.execute(
            "DELETE FROM retreat_options WHERE board_id=? AND phase=?",
            (board.board_id, board.get_phase_and_year_string()),
        )
        cursor.execute(
            "DELETE FROM vassal_orders WHERE board_id=? AND phase=?",
            (board.board_id, board.get_phase_and_year_string()),
        )
        cursor.close()
        self._connection.commit()

    def total_delete(self, board: Board):
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM boards WHERE board_id=?", (board.board_id,))
        cursor.execute("DELETE FROM provinces WHERE board_id=?", (board.board_id,))
        cursor.execute("DELETE FROM units WHERE board_id=?", (board.board_id,))
        cursor.execute("DELETE FROM builds WHERE board_id=?", (board.board_id,))
        cursor.execute(
            "DELETE FROM retreat_options WHERE board_id=?", (board.board_id,)
        )
        cursor.execute("DELETE FROM players WHERE board_id=?", (board.board_id,))
        cursor.execute("DELETE FROM spec_requests WHERE server_id=?", (board.board_id,))
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
