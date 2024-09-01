import re, sys
from xml.etree.ElementTree import Element, ElementTree

from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType


# noinspection PyProtectedMember
def get_svg_element_by_id(svg_root: ElementTree, element_id: str) -> Element:
    return svg_root.xpath(f'//*[@id="{element_id}"]')[0]


# NOTE: better way to do this DRY would be making a Transform class that can be applied to a coordinate and combining
# these two functions into one. For now, I'm just doing it this way.
def get_translation_for_element(element: Element) -> tuple[float, float]:
    transform_string = element.get("transform", None)

    if not transform_string:
        return 0, 0

    translation_match = re.search("^\\s*translate\\((.*),(.*)\\)\\s*", transform_string)
    if not translation_match:
        print(
            f"Could not parse translate string {transform_string} on element with id {element.get("id", None)}",
            file=sys.stderr,
        )
        return 0, 0

    return float(translation_match.group(1)), float(translation_match.group(2))


def get_matrix_transform_for_element(element: Element) -> tuple[float, float, float, float, float, float]:
    transform_string = element.get("transform", None)

    if not transform_string:
        return 1, 0, 0, 1, 0, 0

    translation_match = re.search("^\\s*matrix\\((.*),(.*),(.*),(.*),(.*),(.*)\\)\\s*", transform_string)
    if not translation_match:
        print(
            f"Could not parse matrix transform string {transform_string} on element with id {element.get("id", None)}",
            file=sys.stderr,
        )
        return 1, 0, 0, 1, 0, 0

    # It kept whining at me about returning the wrong type when I did it in different ways
    # I could suppress warning or find a way that doesn't throw warnings, but you know what? this works
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


def _get_unit_coordinates_and_radius(
    unit_data: Element,
) -> tuple[tuple[float, float], float]:
    path: Element = unit_data.find("{http://www.w3.org/2000/svg}path")
    x = float(path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx"))
    y = float(path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy"))
    r = float(path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}r2"))

    x_dx, y_dx, x_dy, y_dy, x_c, y_c = get_matrix_transform_for_element(path)
    x = x_dx * x + y_dx * y + x_c
    y = x_dy * x + y_dy * y + y_c
    # Not sure what to do with r, but we don't use it anyway

    return (x, y), r


def add_tuples(*args: tuple[float, float]):
    return sum([item[0] for item in args]), sum([item[1] for item in args])
