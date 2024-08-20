from diplomacy.adjudicator.adjudicator import Adjudicator
from diplomacy.persistence.board import Board
from diplomacy.persistence.order import Move, Support, Hold
from diplomacy.persistence.phase import spring_moves
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, ProvinceType
from diplomacy.persistence.unit import Unit, UnitType

# the pydip library is not super clear, so we're going to have some tests around here that let us figure out what's
# going on via the debugger.
if __name__ == "__main__":
    player1 = Player("player 1", "", set(), set())
    player2 = Player("player 2", "", set(), set())

    province1 = Province("province 1", [], ProvinceType.LAND, True, None, None, None)
    province2 = Province("province 2", [], ProvinceType.LAND, True, None, None, None)
    province3 = Province("province 3", [], ProvinceType.LAND, True, None, None, None)

    province1.set_adjacent({province2, province3})
    province2.set_adjacent({province1, province3})
    province3.set_adjacent({province1, province2})

    unit1 = Unit(UnitType.ARMY, player1, province1)
    unit2 = Unit(UnitType.ARMY, player1, province2)
    unit3 = Unit(UnitType.ARMY, player2, province3)

    player1.units.add(unit1)
    player1.units.add(unit2)
    player2.units.add(unit3)

    province1.unit = unit1
    province2.unit = unit2
    province3.unit = unit3

    players = {player1, player2}
    provinces = {province1, province2, province3}
    units = {unit1, unit2, unit3}
    orders = {
        unit1: Move(unit1, province3),
        unit2: Support(unit2, unit1, province3),
        unit3: Hold(unit3),
    }

    board = Board(players, provinces, units, orders, set(), spring_moves)
    adjudicator = Adjudicator(board)
    adjudicator.adjudicate()
