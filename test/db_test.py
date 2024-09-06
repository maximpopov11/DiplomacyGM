import json
import os

import diplomacy.persistence.db.database as db
from diplomacy.map_parser.vector.vector import Parser
from diplomacy.persistence.unit import Unit, UnitType


def run() -> None:
    # noinspection PyProtectedMember
    database = db._DatabaseConnection(db_file=":memory:")
    assert len(database.get_boards()) == 0

    board_parser = Parser()
    board = board_parser.parse()
    corse = board.get_province("corse")
    ayutthaya = board.get_player("ayutthaya")
    aymara = board.get_player("aymara")
    corse.owner = ayutthaya
    corse.dislodged_unit = Unit(UnitType.ARMY, ayutthaya, corse, None, None)
    corse.unit = Unit(UnitType.FLEET, aymara, corse, corse.coast(), None)
    board.units.add(corse.dislodged_unit)
    board.units.add(corse.unit)
    database.save_board(0, board)

    boards = database.get_boards()
    assert len(boards) == 1

    retrieved_board = boards[0]
    assert {player.name for player in retrieved_board.players} == {player.name for player in board.players}
    retrieved_corse = retrieved_board.get_province("corse")
    assert retrieved_corse.owner.name == corse.owner.name
    assert retrieved_corse.unit.player.name == corse.unit.player.name
    assert retrieved_corse.dislodged_unit.player.name == corse.dislodged_unit.player.name
    assert retrieved_corse.unit.coast.name == corse.unit.coast.name
