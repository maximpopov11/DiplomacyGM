from diplomacy.adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.vector import Parser
from diplomacy.persistence import order
from diplomacy.persistence.unit import UnitType
from test.utils import test

# bot.run()

test()

board = Parser().parse()

paris = next((unit for unit in board.units if unit.province.name == "Paris"), None)
nantes = next((unit for unit in board.units if unit.province.name == "Nantes"), None)
bordeaux = next((unit for unit in board.units if unit.province.name == "Bordeaux"), None)
marseille = next((unit for unit in board.units if unit.province.name == "Marseille"), None)
dijon = next((unit for unit in board.units if unit.province.name == "Dijon"), None)
barcelona = next((unit for unit in board.units if unit.province.name == "Barcelona"), None)
orleans = next((province for province in board.provinces if province.name == "Orleans"), None)
corse = next((province for province in board.provinces if province.name == "Corse"), None)
ghent = next((province for province in board.provinces if province.name == "Ghent"), None)
board.unit_orders = {
    paris: order.Hold(paris),
    nantes: order.Core(nantes),
    bordeaux: order.Move(bordeaux, orleans),
    marseille: order.ConvoyTransport(marseille, dijon, corse),
    dijon: order.Support(dijon, bordeaux, orleans),
    barcelona: order.RetreatDisband(barcelona),
}
board.build_orders = {
    order.Build(ghent, UnitType.ARMY),
}

Mapper(board).get_moves_map(None)

# TODO: priorities: (MAP), (ALPHA), <game happens here>, (DB), (BETA)

# TODO: (ALPHA) update readme (how to use bot)
# TODO: (ALPHA) conduct testing: test solo, test group, live game test

# TODO: (DB) setup DB and test db write & db read
# TODO: (DB) assert that the DB is backed up (needs to be a current up-to-date backup)

# TODO: (BETA) me only command for editing all game map state without permanence restriction (ex. province adjacency)
# TODO: (BETA) don't rely on PyDip, it's so much easier to update things when I own all of the code and write it pretty
# TODO: (BETA) add requirements.txt
# TODO: (BETA) clean up configs
# TODO: (BETA) support SVGs with minimal overhead
# TODO: (BETA) support raster images
# TODO: (BETA) add classic map example & update readme
