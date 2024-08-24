import svgwrite

from diplomacy.persistence.board import Board
from diplomacy.persistence.player import Player


class Mapper:
    def __init__(self, board: Board):
        self.board: Board = board

    def get_moves_map(self, player_restriction: Player | None) -> str:
        drawing = svgwrite.Drawing("test.svg")
        cx, cy, r = 100, 100, 50
        drawing.add(drawing.circle(center=(cx, cy), r=r, fill="red"))
        drawing.save()

        # TODO: (MAP) check player restriction (to limit what orders are drawn)
        # TODO: (MAP) copy SVG
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
