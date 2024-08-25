from xml.etree.ElementTree import Element, ElementTree

from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType


def get_layer_data(svg_root: ElementTree, layer_id: str) -> list[Element]:
    return svg_root.xpath(f'//*[@id="{layer_id}"]')[0].getchildren()


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
        return UnitType.ARMY
    elif num_sides == "6":
        return UnitType.FLEET
    else:
        raise RuntimeError(f"Unit has {num_sides} sides which does not match any unit definition.")


def _get_unit_coordinates_and_radius(
    unit_data: Element,
    translation: tuple[float, float] = (0, 0),
) -> tuple[tuple[float, float], float]:
    x = float(unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx"))
    y = float(unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy"))
    r = float(unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}r2"))

    x += translation[0]
    y += translation[1]
    return (x, y), r


def get_translation(element: Element) -> tuple[float, float]:
    string = element.get("transform")
    prefix = "translate("
    if not string.startswith(prefix):
        raise RuntimeError(f"Translation transform expected, got: {string}")

    string = string[len(prefix) : len(string) - 1]
    nums: list[string] = string.split(",")

    return float(nums[0]), float(nums[1])
