from xml.etree.ElementTree import Element

from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType


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


def _get_unit_coordinates(unit_data: Element) -> tuple[tuple[float, float], float]:
    x: str = unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx")
    y: str = unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy")
    r: str = unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}r2")
    coordinate: tuple[float, float] = (float(x), float(y))
    radius = float(r)
    return coordinate, radius
