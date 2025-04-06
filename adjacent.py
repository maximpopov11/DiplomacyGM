#%
import os

os.environ["simultaneous_svg_exports_limit"] = "1"

import main
import diplomacy.persistence.manager as manager
from diplomacy.adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.utils import get_svg_element
x = manager.Manager()

x.create_game(1, "impdipfow.json")

#%
b = x.get_board(1)
a = Mapper(b)
arrow_layer = get_svg_element(a.state_svg, a.board.data["svg config"]["arrow_output"])

import re

def exclude(name: str) -> bool:
    if re.compile('[NSI][NAP]O').match(name):
        return True
    return name == "Chukchi Sea"

for province in b.provinces:
    if exclude(province.name):
        continue
    for adjacent in province.adjacent:
        if exclude(adjacent.name):
            continue
        curr = province.primary_unit_coordinate
        othe = adjacent.primary_unit_coordinate
        path = f"M {curr[0]},{curr[1]} L {othe[0]} {othe[1]}"
        order_path = a._draw_path(path, marker_end="ball")
        arrow_layer.append(order_path)

with open("test.svg", "wb") as f:
    f.write(a.draw_current_map()[0])