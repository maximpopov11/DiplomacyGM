from xml.etree.ElementTree import Element, ElementTree

from diplomacy.map_parser.vector.transform import EmptyTransform, get_transform
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
        x = float(x)
        y = float(y)
        #TODO: if there are multiple layers of transforms we need to do them all
        x, y = get_transform(unit_data).transform((x, y))
    x = float(x)
    y = float(y)
    return get_transform(path).transform((x, y))
