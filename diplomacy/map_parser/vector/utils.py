from xml.etree.ElementTree import Element, ElementTree

from diplomacy.map_parser.vector.transform import MatrixTransform, get_transform
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType


def get_svg_element(svg_root: ElementTree, element_id: str) -> Element:
    return svg_root.xpath(f'//*[@id="{element_id}"]')[0]

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
        raise RuntimeError(f"Unit has {num_sides} sides which does not match any unit definition.")


def get_unit_coordinates(
    unit_data: Element,
) -> tuple[float, float]:
    path: Element = unit_data.find("{http://www.w3.org/2000/svg}path")
    x = float(path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx"))
    y = float(path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy"))
    return get_transform(path).transform((x, y))
