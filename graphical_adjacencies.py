import os
import re

os.environ["simultaneous_svg_exports_limit"] = "1"

import main
from diplomacy.persistence.manager import Manager, get_parser
from diplomacy.adjudicator.mapper import Mapper
from diplomacy.map_parser.vector.utils import get_svg_element
from lxml import etree
manager = Manager()

try:
    manager.total_delete(0)
except KeyError:
    pass

game_type = "impdipfow.json"

manager.create_game(0, game_type)

#%
board = manager.get_board(0)
mapper = Mapper(board)

parser = get_parser(game_type)

hover_text = """
function setColor(province_name, color) {
    for (let e of document.getElementsByClassName(province_name)) {
        e.setAttribute("stroke", color);
    }
}
"""

hover_fn = etree.Element("script")
hover_fn.text = hover_text

arrow_layer = get_svg_element(mapper.state_svg, mapper.board.data["svg config"]["arrow_output"])

arrow_layer.append(hover_fn)

for layer in (parser.land_layer, parser.island_layer, parser.sea_layer):
    print(layer)
    for province_data in layer.getchildren():
        name = parser._get_province_name(province_data)
        province_data.attrib["onmouseover"] = f"setColor({name}, 'red')"
        province_data.attrib["onmouseout" ] = f"setColor({name}, '')"

def exclude(name: str) -> bool:
    if re.compile('[NSI][NAP]O').match(name):
        return True
    return name == "Chukchi Sea"


for province in board.provinces:
    if exclude(province.name):
        continue
    for adjacent in province.adjacent:
        if exclude(adjacent.name):
            continue
        curr = province.primary_unit_coordinate
        othe = adjacent.primary_unit_coordinate
        path = f"M {curr[0]},{curr[1]} L {othe[0]} {othe[1]}"
        order_path = mapper._draw_path(path, marker_end="")
        order_path.attrib["class"] = province.name
        order_path.attrib["stroke"] = ""
        arrow_layer.append(order_path)


with open("test.svg", "wb") as f:
    f.write(mapper.draw_current_map()[0])