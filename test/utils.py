from lxml import etree

from diplomacy.map_parser.vector.config_svg import SVG_PATH
from diplomacy.map_parser.vector.vector import Parser


# draw small red circle at position to highlight it on the map
def _highlight_position(coordinate: tuple[float, float]) -> None:
    svg = etree.parse(SVG_PATH)
    root = svg.getroot()
    circle = etree.Element(
        "circle",
        {
            "cx": str(coordinate[0]),
            "cy": str(coordinate[1]),
            "r": "5",
            "fill": "red",
            "stroke": "black",
            "stroke-width": "1",
        },
    )
    root.append(circle)
    svg.write("highlighted.svg")


def test() -> None:
    board = Parser().parse()
    name = "Paris"
    coordinate = next((province.primary_unit_coordinate for province in board.provinces if province.name == name), None)
    _highlight_position(coordinate)
