from diplomacy.adjudicator.adjudicator import Adjudicator
from diplomacy.map_parser.vector import vector
from diplomacy.persistence import order
from diplomacy.persistence.board import Board


# the pydip library is not super clear, so we're going to have some tests around here that let us figure out what's
# going on via the debugger.
def run() -> None:
    board = vector.Parser().parse()

    # spring moves
    paris = board.get_province("Paris")
    ghent = board.get_province("Ghent")
    board.unit_orders[paris.unit] = order.Move(paris.unit, ghent)
    _adjudicate(board)

    # fall moves
    amsterdam = board.get_province("Amsterdam")
    utrecht = board.get_province("Utrecht")
    board.unit_orders[amsterdam.unit] = order.Move(amsterdam.unit, ghent)
    board.unit_orders[utrecht.unit] = order.Support(utrecht.unit, amsterdam.unit, ghent)
    _adjudicate(board)

    # fall retreats
    board.unit_orders[ghent.unit] = order.RetreatMove(ghent.unit, paris)
    _adjudicate(board)


def _adjudicate(board: Board) -> None:
    adjudicator = Adjudicator(board)
    adjudicator.adjudicate()
