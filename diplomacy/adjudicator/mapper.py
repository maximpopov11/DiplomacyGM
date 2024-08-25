from xml.etree.ElementTree import ElementTree

from lxml import etree

from diplomacy.map_parser.vector.config_svg import SVG_PATH
from diplomacy.persistence.board import Board
from diplomacy.persistence.order import (
    Order,
    Hold,
    Core,
    ConvoyTransport,
    Support,
    RetreatMove,
    RetreatDisband,
    Build,
    Disband,
    Move,
    ConvoyMove,
)
from diplomacy.persistence.player import Player


class Mapper:
    def __init__(self, board: Board):
        self.board: Board = board
        self.svg: ElementTree = etree.parse(SVG_PATH)
        self.stroke_width: int = 2

    def get_moves_map(self, player_restriction: Player | None) -> str:
        for order in self.board.get_orders():
            if player_restriction and order.player != player_restriction:
                continue
            self._draw(order)
        self.svg.write("moves_map.svg")
        # TODO: (DB) let's not have a ton of old files: delete after putting in DB
        # TODO: (MAP) return svg
        raise RuntimeError("Get moves map has not yet been implemented.")

    def get_results_map(self) -> str:
        # TODO: (MAP) copy SVG
        # TODO: (MAP) update unit positions (and location labels as a backup)
        # TODO: (MAP) update province colors (island borders need to get colored in alongside the island fill)
        # TODO: (MAP) update center (core) colors
        # TODO: (MAP) return copy SVG
        raise RuntimeError("Get results map has not yet been implemented.")

    def _draw_hold(self, order: Hold) -> None:
        element = self.svg.getroot()
        drawn_order = etree.Element(
            "circle",
            {
                "cx": order.unit.coordinate[0],
                "cy": order.unit.coordinate[1],
                "r": order.unit.radius + order.unit.radius / 3,
                "fill": "none",
                "stroke": "black",
                "stroke-width": self.stroke_width,
            },
        )
        element.append(drawn_order)

    def _draw_core(self, order: Core) -> None:
        element = self.svg.getroot()
        drawn_order = etree.Element(
            "rect",
            {
                "x": order.unit.coordinate[0] - order.unit.radius * 1.2,
                "y": order.unit.coordinate[1] - order.unit.radius * 1.2,
                "width": order.unit.radius + order.unit.radius * 1.2 * 2,
                "height": order.unit.radius + order.unit.radius * 1.2 * 2,
                "fill": "none",
                "stroke": "green",
                "stroke-width": self.stroke_width,
                "transform": "rotate(45 100 100)",
            },
        )
        element.append(drawn_order)

    def _draw_move(self, order: Move | ConvoyMove | RetreatMove) -> None:
        element = self.svg.getroot()
        drawn_order = etree.Element(
            "line",
            {
                "x1": order.unit.coordinate[0],
                "y1": order.unit.coordinate[1],
                "x2": order.destination.primary_unit_coordinate[0],
                "y2": order.destination.primary_unit_coordinate[1],
                "fill": "none",
                "stroke": "black",
                "stroke-width": self.stroke_width,
            },
        )
        element.append(drawn_order)

    def _draw_support(self, order: Support) -> None:
        element = self.svg.getroot()
        x1 = order.unit.province.primary_unit_coordinate[0]
        y1 = order.unit.province.primary_unit_coordinate[1]
        x2 = order.source.province.primary_unit_coordinate[0]
        y2 = order.source.province.primary_unit_coordinate[1]
        x3 = order.destination.primary_unit_coordinate[0]
        y3 = order.destination.primary_unit_coordinate[1]
        path = f"M {x1},{y1} {x2},{y2} {x3},{y3}"
        drawn_order = etree.Element(
            "path",
            {
                "d": path,
                "fill": "none",
                "stroke": "black",
                "stroke-width": self.stroke_width,
            },
        )
        element.append(drawn_order)

    def _draw_convoy(self, order: ConvoyTransport) -> None:
        element = self.svg.getroot()
        x1 = order.source.province.primary_unit_coordinate[0]
        y1 = order.source.province.primary_unit_coordinate[1]
        x2 = order.unit.province.primary_unit_coordinate[0]
        y2 = order.unit.province.primary_unit_coordinate[1]
        x3 = order.destination.primary_unit_coordinate[0]
        y3 = order.destination.primary_unit_coordinate[1]
        path = f"M {x1},{y1} {x2},{y2} {x3},{y3}"
        drawn_order = etree.Element(
            "path",
            {
                "d": path,
                "fill": "none",
                "stroke": "black",
                "stroke-width": self.stroke_width,
            },
        )
        element.append(drawn_order)

    def _draw_build(self, order: Build) -> None:
        element = self.svg.getroot()
        drawn_order = etree.Element(
            "circle",
            {
                "cx": order.province.primary_unit_coordinate[0],
                "cy": order.province.primary_unit_coordinate[1],
                "r": 10,
                "fill": "none",
                "stroke": "green",
                "stroke-width": self.stroke_width,
            },
        )
        element.append(drawn_order)

    def _draw_disband(self, order: RetreatDisband | Disband) -> None:
        element = self.svg.getroot()
        drawn_order = etree.Element(
            "circle",
            {
                "cx": order.unit.coordinate[0],
                "cy": order.unit.coordinate[1],
                "r": order.unit.radius + order.unit.radius / 3,
                "fill": "none",
                "stroke": "red",
                "stroke-width": self.stroke_width,
            },
        )
        element.append(drawn_order)

    def _draw(self, order: Order) -> None:
        # TODO: (BETA) draw failed moves on adjudication (not player check) in red
        # TODO: (MAP) draw arrowhead for move, convoy, support
        if isinstance(order, Hold):
            self._draw_hold(order)
        if isinstance(order, Core):
            self._draw_core(order)
        if isinstance(order, Move):
            self._draw_move(order)
        if isinstance(order, ConvoyMove):
            self._draw_move(order)
        if isinstance(order, Support):
            self._draw_support(order)
        if isinstance(order, ConvoyTransport):
            self._draw_convoy(order)
        if isinstance(order, RetreatMove):
            self._draw_move(order)
        if isinstance(order, RetreatDisband):
            self._draw_disband(order)
        if isinstance(order, Build):
            self._draw_build(order)
        if isinstance(order, Disband):
            self._draw_disband(order)
        else:
            raise RuntimeError(f"Unknown order type: {order.__class__}")
