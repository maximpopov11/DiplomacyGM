from diplomacy.adjudicator.adjudicator import Adjudicator
from diplomacy.persistence.board import Board
from diplomacy.persistence.phase import spring_moves
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, ProvinceType
from diplomacy.persistence.unit import Unit, UnitType

# the pydip library is not super clear, so we're going to have some tests around here that let us figure out what's
# going on via the debugger.
if __name__ == "__main__":
    player1 = Player("player 1", "color 1", set(), set())
    province1 = Province("province 1", [], ProvinceType.LAND, True, None, None, None)
    unit1 = Unit(UnitType.ARMY, player1, province1)
    player1.units.add(unit1)

    players = {player1}
    provinces = {province1}
    units = {unit1}

    board = Board(players, provinces, units, {}, set(), spring_moves)
    adjudicator = Adjudicator(board)
    adjudicator.adjudicate()
