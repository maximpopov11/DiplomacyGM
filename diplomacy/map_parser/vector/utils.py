from xml.etree.ElementTree import Element, ElementTree

from diplomacy.map_parser.vector.transform import MatrixTransform, get_transform
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType


def get_svg_element(svg_root: ElementTree, element_id: str) -> Element:
    try:
        return svg_root.xpath(f'//*[@id="{element_id}"]')[0]
    except:
        print(element_id)

def get_element_color(element: Element) -> str:
    style = element.get("style").split(";")
    for value in style:
        prefix = "fill:#"
        if value.startswith(prefix):
            return value[len(prefix) :]


def get_player(element: Element, color_to_player: dict[str, Player]) -> Player:
    return color_to_player[get_element_color(element)]

def _get_unit_type(unit_data: Element) -> UnitType:
    num_sides = unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}sides")
    if num_sides == "3":
        return UnitType.FLEET
    elif num_sides == "6":
        return UnitType.ARMY
    else:
        return UnitType.ARMY
        raise RuntimeError(f"Unit has {num_sides} sides which does not match any unit definition.")


def get_unit_coordinates(
    unit_data: Element,
) -> tuple[float, float]:
    path: Element = unit_data.find("{http://www.w3.org/2000/svg}path")

    x = path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx")
    y = path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy")
    if x == None or y == None:
        start = path.get("d")
        start = start.split(" ")[1]
        x, y = start.split(",")
        #TODO: if there are multiple layers of transforms we need to do them all
        trans = get_transform(unit_data)
    else:
        trans = get_transform(path)
    x = float(x)
    y = float(y)
    return trans.transform((x, y))
            