import os
import re

os.environ["simultaneous_svg_exports_limit"] = "1"

import main
import numpy as np
from diplomacy.persistence.manager import Manager, get_parser
from diplomacy.adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.vector import initialize_province_resident_data
from diplomacy.map_parser.vector.utils import get_svg_element
from diplomacy.persistence.province import Province, Location, Coast, get_adjacent_provinces
from lxml import etree
from diplomacy.map_parser.vector.transform import TransGL3
manager = Manager()

try:
    manager.total_delete(0)
except KeyError:
    pass

game_type = "impdipfow.json"

manager.create_game(0, game_type)

board = manager.get_board(0)
board.fow = False
mapper = Mapper(board)

# miwok = board.name_to_province["miwok"].coast()
# import pdb
# pdb.set_trace()
# x = miwok.get_adjacent_coasts()
# print(x)