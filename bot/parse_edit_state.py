from bot.utils import get_phase, get_unit_type, get_keywords
from diplomacy.custom_adjudicator.mapper import Mapper
from diplomacy.persistence.board import Board
from diplomacy.persistence.phase import is_retreats_phase
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.unit import UnitType

_set_phase_str = "set phase"
_set_core_str = "set core"
_set_half_core_str = "set half core"
_set_province_owner_str = "set province owner"
_create_unit_str = "create unit"
_create_dislodged_unit_str = "create dislodged unit"
_delete_unit_str = "delete unit"
_delete_dislodged_unit_str = "delete dislodged unit"
_move_unit_str = "move unit"
_dislodge_unit_str = "dislodge unit"
_make_units_claim_provinces_str = "make units claim provinces"


def parse_edit_state(message: str, board: Board) -> tuple[str, str | None]:
    invalid: list[tuple[str, Exception]] = []
    commands = str.splitlines(message)
    if commands[0].strip() == ".edit":
        commands = commands[1:]
    for command in commands:
        try:
            _parse_command(command, board)
        except Exception as error:
            invalid.append((command, error))

    if invalid:
        response = "The following commands were invalid:"
        for command in invalid:
            response += f"\n{command[0]} with error: {command[1]}"
    else:
        response = "Commands validated successfully. Results map updated."

    # TODO: (DB) return map as the response
    svg_file_name = Mapper(board).draw_current_map()

    return response, svg_file_name


def _parse_command(command: str, board: Board) -> None:
    command = command.lower()
    keywords: list[str] = get_keywords(command)
    if keywords[0].strip() == ".edit":
        keywords = keywords[1:]
    command_type = keywords[0]
    keywords = keywords[1:]

    if command_type == _set_phase_str:
        _set_phase(keywords, board)
    elif command_type == _set_core_str:
        _set_province_core(keywords, board)
    elif command_type == _set_half_core_str:
        _set_province_half_core(keywords, board)
    elif command_type == _set_province_owner_str:
        _set_province_owner(keywords, board)
    elif command_type == _create_unit_str:
        _create_unit(keywords, board)
    elif command_type == _create_dislodged_unit_str:
        _create_dislodged_unit(keywords, board)   
    elif command_type == _delete_unit_str:
        _delete_unit(keywords, board)
    elif command_type == _move_unit_str:
        _move_unit(keywords, board)
    elif command_type == _dislodge_unit_str:
        _dislodge_unit(keywords, board)
    elif command_type == _make_units_claim_provinces_str:
        _make_units_claim_provinces(keywords, board)
    elif command_type == _delete_dislodged_unit_str:
        _delete_dislodged_unit(keywords, board)
    else:
        raise RuntimeError(f"No command key phrases found")


def _set_phase(keywords: list[str], board: Board) -> None:
    old_phase_string = board.get_phase_and_year_string()
    new_phase = get_phase(keywords[0])
    if new_phase is None:
        raise ValueError(f"{keywords[0]} is not a valid phase name")
    board.phase = new_phase
    get_connection().execute_arbitrary_sql(
        "UPDATE boards SET phase=? WHERE board_id=? and phase=?",
        (board.get_phase_and_year_string(), board.board_id, old_phase_string),
    )
    get_connection().execute_arbitrary_sql(
        "UPDATE provinces SET phase=? WHERE board_id=? and phase=?",
        (board.get_phase_and_year_string(), board.board_id, old_phase_string),
    )
    get_connection().execute_arbitrary_sql(
        "UPDATE units SET phase=? WHERE board_id=? and phase=?",
        (board.get_phase_and_year_string(), board.board_id, old_phase_string),
    )


def _set_province_core(keywords: list[str], board: Board) -> None:
    province = board.get_province(keywords[0])
    player = board.get_player(keywords[1])
    province.core = player
    get_connection().execute_arbitrary_sql(
        "UPDATE provinces SET core=? WHERE board_id=? and phase=? and province_name=?",
        (player.name if player is not None else None, board.board_id, board.get_phase_and_year_string(), province.name),
    )


def _set_province_half_core(keywords: list[str], board: Board) -> None:
    province = board.get_province(keywords[0])
    player = board.get_player(keywords[1])
    province.half_core = player
    get_connection().execute_arbitrary_sql(
        "UPDATE provinces SET half_core=? WHERE board_id=? and phase=? and province_name=?",
        (player.name if player is not None else None, board.board_id, board.get_phase_and_year_string(), province.name),
    )


def _set_province_owner(keywords: list[str], board: Board) -> None:
    province = board.get_province(keywords[0])
    player = board.get_player(keywords[1])
    board.change_owner(province, player)
    get_connection().execute_arbitrary_sql(
        "UPDATE provinces SET owner=? WHERE board_id=? and phase=? and province_name=?",
        (player.name if player is not None else None, board.board_id, board.get_phase_and_year_string(), province.name),
    )


def _create_unit(keywords: list[str], board: Board) -> None:
    unit_type = get_unit_type(keywords[0])
    player = board.get_player(keywords[1])
    province, coast = board.get_province_and_coast(keywords[2])
    unit = board.create_unit(unit_type, player, province, coast, None)
    get_connection().execute_arbitrary_sql(
        "INSERT INTO units (board_id, phase, location, is_dislodged, owner, is_army) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (board_id, phase, location, is_dislodged) DO UPDATE SET owner=?, is_army=?",
        (
            board.board_id,
            board.get_phase_and_year_string(),
            unit.get_location().name,
            False,
            player.name,
            unit_type == UnitType.ARMY,
            player.name,
            unit_type == UnitType.ARMY,
        ),
    )
    
def _create_dislodged_unit(keywords: list[str], board: Board) -> None:
	if is_retreats_phase(board.phase):
		unit_type = get_unit_type(keywords[0])
		player = board.get_player(keywords[1])
		province, coast = board.get_province_and_coast(keywords[2])
		retreat_options = set([board.get_province(province_name) for province_name in keywords [3:]])
		unit = board.create_unit(unit_type, player, province, coast, retreat_options)
		get_connection().execute_arbitrary_sql(
		"INSERT INTO units (board_id, phase, location, is_dislodged, owner, is_army) "
		"VALUES (?, ?, ?, ?, ?, ?) "
		"ON CONFLICT (board_id, phase, location, is_dislodged) DO UPDATE SET owner=?, is_army=?",
		(
		    board.board_id,
		    board.get_phase_and_year_string(),
		    unit.get_location().name,
		    True,
		    player.name,
		    unit_type == UnitType.ARMY,
		    player.name,
		    unit_type == UnitType.ARMY,
		),
		)
	else:
		raise RuntimeError("Cannot create a dislodged unit in move phase") 


def _delete_unit(keywords: list[str], board: Board) -> None:
    province = board.get_province(keywords[0])
    unit = board.delete_unit(province)
    get_connection().execute_arbitrary_sql(
        "DELETE FROM units WHERE board_id=? and phase=? and location=? and is_dislodged=?",
        (board.board_id, board.get_phase_and_year_string(), unit.get_location().name, False),
    )


def _delete_dislodged_unit(keywords: list[str], board: Board) -> None:
    province = board.get_province(keywords[0])
    unit = board.delete_dislodged_unit(province)
    get_connection().execute_arbitrary_sql(
        "DELETE FROM units WHERE board_id=? and phase=? and location=? and is_dislodged=?",
        (board.board_id, board.get_phase_and_year_string(), unit.get_location().name, True),
    )


def _move_unit(keywords: list[str], board: Board) -> None:
    old_province = board.get_province(keywords[0])
    unit = old_province.unit
    old_location = unit.get_location()
    new_location = board.get_location(keywords[1])
    board.move_unit(unit, new_location)
    get_connection().execute_arbitrary_sql(
        "DELETE FROM units WHERE board_id=? and phase=? and location=? and is_dislodged=?",
        (board.board_id, board.get_phase_and_year_string(), old_location.name, False),
    )
    get_connection().execute_arbitrary_sql(
        "INSERT INTO units (board_id, phase, location, is_dislodged, owner, is_army) VALUES (?, ?, ?, ?, ?, ?)",
        (
            board.board_id,
            board.get_phase_and_year_string(),
            unit.get_location().name,
            False,
            unit.player.name,
            unit.unit_type == UnitType.ARMY,
        ),
    )

def _dislodge_unit(keywords: list[str], board: Board) -> None:
	if is_retreats_phase(board.phase):
		province = board.get_province(keywords[0])
		if province.dislodged_unit != None:
			raise RuntimeError("Dislodged unit already exists in province") 
		unit = province.unit
		if unit == None:
			raise RuntimeError("No unit to dislodge in province")
		retreat_options = set([board.get_province(province_name) for province_name in keywords [1:]])
		dislodged_unit = board.create_unit(unit.unit_type, unit.player, unit.province, unit.coast, retreat_options)
		unit = board.delete_unit(province)
		get_connection().execute_arbitrary_sql(
		"UPDATE units SET is_dislodged = True where board_id=? and phase=? and location=?",
		(board.board_id, board.get_phase_and_year_string(), province.name),
		)
	else:
		raise RuntimeError("Cannot create a dislodged unit in move phase") 

def _make_units_claim_provinces(keywords, board):
    claim_centers = False
    if keywords:
        claim_centers = keywords[0].lower() == "true"
    for unit in board.units:
        if claim_centers or not unit.province.has_supply_center:
            board.change_owner(unit.province, unit.player)
            get_connection().execute_arbitrary_sql(
                "UPDATE provinces SET owner=? WHERE board_id=? and phase=? and province_name=?",
                (unit.player.name, board.board_id, board.get_phase_and_year_string(), unit.province.name),
            )
