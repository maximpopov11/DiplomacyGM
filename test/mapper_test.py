from diplomacy.adjudicator.mapper import Mapper
from diplomacy.map_parser.vector import vector
from diplomacy.persistence import order
from diplomacy.persistence.unit import UnitType


def run() -> None:
    board = vector.Parser().parse()

    france = board.get_player("France")
    paris = board.get_province("Paris")
    nantes = board.get_province("Nantes")
    bordeaux = board.get_province("Bordeaux")
    marseille = board.get_province("Marseille")
    dijon = board.get_province("Dijon")
    barcelona = board.get_province("Barcelona")
    orleans = board.get_province("Orleans")
    corse = board.get_province("Paris")
    ghent = board.get_province("Ghent")

    paris.unit.order = order.Hold()
    nantes.unit.order = order.Core()
    bordeaux.unit.order = order.Move(orleans)
    marseille.unit.order = order.ConvoyTransport(dijon.unit, corse)
    dijon.unit.order = order.Support(bordeaux.unit, orleans)
    barcelona.unit.order = order.RetreatDisband()
    france.build_orders.add(order.Build(ghent, UnitType.ARMY))

    Mapper(board).get_moves_map(None)
