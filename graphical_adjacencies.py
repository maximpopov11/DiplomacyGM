#%
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

#%


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

for layer in (get_svg_element(mapper.state_svg, parser.layers["land_layer"]), get_svg_element(mapper.state_svg, parser.layers["island_borders"]), get_svg_element(mapper.state_svg, parser.layers["sea_borders"])):
    for province_data in layer.getchildren():
        name = parser._get_province_name(province_data).replace("'", "_")
        province_data.attrib["onmouseover"] = f"setColor('~{name} coast~', 'black')"
        province_data.attrib["onmouseout" ] = f"setColor('~{name} coast~', '')"

for province in board.provinces:
    # for adjacent in province.adjacent:
    #     curr = province.primary_unit_coordinate
    #     othe = adjacent.primary_unit_coordinate
    #     path = f"M {curr[0]},{curr[1]} L {othe[0]} {othe[1]}"
    #     order_path = mapper._draw_path(path, marker_end="")
    #     order_path.attrib["class"] = f"~{province.name}~"
    #     order_path.attrib["stroke"] = ""
    #     arrow_layer.append(order_path)
    for coast in province.coasts:
        for loc in get_adjacent_provinces(coast):
            curr = coast.primary_unit_coordinate
            othe = loc.primary_unit_coordinate
            path = f"M {curr[0]},{curr[1]} L {othe[0]} {othe[1]}"
            order_path = mapper._draw_path(path, marker_end="")
            name = coast.name.replace("'", "_")
            order_path.attrib["class"] = f"~{name}~"
            order_path.attrib["stroke"] = ""
            arrow_layer.append(order_path)


get_svg_element(mapper.state_svg, board.data["svg config"]["unit_output"]).clear()
get_svg_element(mapper.state_svg, board.data["svg config"]["province_names"]).clear()

coasts = get_svg_element(mapper.state_svg, "layer18").getchildren()

# will not work if coast markers are substantially changed
text_middle_offset = np.array([3.25, -3.576 / 2])

def get_text_coordinate(e : etree.Element) -> tuple[float, float]:
    trans = TransGL3(e)
    return trans.transform([float(e.attrib["x"]), float(e.attrib["y"])] + text_middle_offset)

def match(p: Province, e: etree.Element):
    print(f"element {e[0].text} is in {p.name}")
    name = p.name.replace("'", "_")
    e.attrib["onmouseover"] = f"setColor('~{name} {e[0].text}~', 'black')"
    e.attrib["onmouseout" ] = f"setColor('~{name} {e[0].text}~', '')"


print(len(coasts))

initialize_province_resident_data(board.provinces, coasts, get_text_coordinate, match)

with open("test.svg", "wb") as f:
    f.write(mapper.draw_current_map()[0])