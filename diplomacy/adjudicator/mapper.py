from lxml import etree

from diplomacy.map_parser.vector.config_svg import SVG_PATH
from diplomacy.persistence.board import Board
from diplomacy.persistence.player import Player


class Mapper:
    def __init__(self, board: Board):
        self.board: Board = board
        self.svg = etree.parse(SVG_PATH)

    def get_moves_map(self, player_restriction: Player | None) -> str:
        self._draw()
        # TODO: (MAP) check player restriction (to limit what orders are drawn)
        # TODO: (MAP) draw orders
        # TODO: (MAP) return copy SVG
        raise RuntimeError("Get moves map has not yet been implemented.")

    def get_results_map(self) -> str:
        # TODO: (MAP) copy SVG
        # TODO: (MAP) update unit positions (and location labels as a backup)
        # TODO: (MAP) update province colors (island borders need to get colored in alongside the island fill)
        # TODO: (MAP) update center (core) colors
        # TODO: (MAP) return copy SVG
        raise RuntimeError("Get results map has not yet been implemented.")

    def _draw(self) -> None:
        element = self.svg.getroot()
        circle = etree.Element(
            "circle",
            {
                "cx": "1000",  # X-coordinate of the center
                "cy": "1000",  # Y-coordinate of the center
                "r": "1000",  # Radius
                "fill": "red",  # Fill color
            },
        )
        element.append(circle)
        self.svg.write("modified.svg")
