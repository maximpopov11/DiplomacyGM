import re
import sys
from xml.etree.ElementTree import Element, ElementTree

from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType


def get_svg_element_by_id(svg_root: ElementTree, element_id: str) -> Element:
    return svg_root.xpath(f'//*[@id="{element_id}"]')[0]


# TODO: (BETA) use SVG library or make a Transform class that can be applied to a coordinate and combine these two func
def get_translation_for_element(element: Element) -> tuple[float, float]:
    transform_string = element.get("transform", None)

    if not transform_string:
        return 0, 0

    translation_match = re.search("^\\s*translate\\((.*),(.*)\\)\\s*", transform_string)
    if not translation_match:
        raise RuntimeError(
            f"Could not parse translate string {transform_string} on element with id {element.get("id", None)}",
        )

    return float(translation_match.group(1)), float(translation_match.group(2))


def get_matrix_transform_for_element(element: Element) -> tuple[float, float, float, float, float, float]:
    transform_string = element.get("transform", None)

    if not transform_string:
        return 1, 0, 0, 1, 0, 0

    translation_match = re.search("^\\s*matrix\\((.*),(.*),(.*),(.*),(.*),(.*)\\)\\s*", transform_string)
    if not translation_match:
        raise RuntimeError(
            f"Could not parse matrix transform string {transform_string} on element with id {element.get("id", None)}",
        )

    return (
        float(translation_match.group(1)),
        float(translation_match.group(2)),
        float(translation_match.group(3)),
        float(translation_match.group(4)),
        float(translation_match.group(5)),
        float(translation_match.group(6)),
    )


def get_player(element: Element, color_to_player: dict[str, Player]) -> Player:
    style = element.get("style").split(";")
    for value in style:
        prefix = "fill:#"
        if value.startswith(prefix):
            color = value[len(prefix) :]
            return color_to_player[color]


def _get_unit_type(unit_data: Element) -> UnitType:
    num_sides = unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}sides")
    if num_sides == "3":
        return UnitType.FLEET
    elif num_sides == "6":
        return UnitType.ARMY
    else:
        raise RuntimeError(f"Unit has {num_sides} sides which does not match any unit definition.")


def _get_unit_coordinates(
    unit_data: Element,
) -> tuple[float, float]:
    path: Element = unit_data.find("{http://www.w3.org/2000/svg}path")
    x = float(path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx"))
    y = float(path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy"))

    x_dx, y_dx, x_dy, y_dy, x_c, y_c = get_matrix_transform_for_element(path)
    x = x_dx * x + y_dx * y + x_c
    y = x_dy * x + y_dy * y + y_c

    return x, y


def add_tuples(*args: tuple[float, float]):
    return sum([item[0] for item in args]), sum([item[1] for item in args])
