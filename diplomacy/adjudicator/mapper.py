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
        self.moves_svg: ElementTree = etree.parse(SVG_PATH)
        self.results_svg: ElementTree = etree.parse(SVG_PATH)
        self.stroke_width: int = 2

    # TODO: (BETA) print svg moves & results files in Discord GM channel
    # TODO: (DB) let's not have a ton of old files: delete moves & results after output (or don't store at all?)
    def get_moves_map(self, player_restriction: Player | None) -> None:
        for order in self.board.get_orders():
            if player_restriction and order.player != player_restriction:
                continue
            self._draw(order)
        self.moves_svg.write("moves_map.svg")

    def get_results_map(self) -> None:
        self._update_units()
        self._update_provinces_and_centers()
        self.moves_svg.write("results_map.svg")

    def _draw_hold(self, order: Hold) -> None:
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
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
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
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
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
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
        element = self.moves_svg.getroot()
        x1 = order.unit.province.primary_unit_coordinate[0]
        y1 = order.unit.province.primary_unit_coordinate[1]
        x2 = order.source.province.primary_unit_coordinate[0]
        y2 = order.source.province.primary_unit_coordinate[1]
        x3 = order.destination.primary_unit_coordinate[0]
        y3 = order.destination.primary_unit_coordinate[1]
        path = f"M {x1},{y1} {x2},{y2} {x3},{y3}"
        drawn_order = _create_element(
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
        element = self.moves_svg.getroot()
        x1 = order.source.province.primary_unit_coordinate[0]
        y1 = order.source.province.primary_unit_coordinate[1]
        x2 = order.unit.province.primary_unit_coordinate[0]
        y2 = order.unit.province.primary_unit_coordinate[1]
        x3 = order.destination.primary_unit_coordinate[0]
        y3 = order.destination.primary_unit_coordinate[1]
        path = f"M {x1},{y1} {x2},{y2} {x3},{y3}"
        drawn_order = _create_element(
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
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
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
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
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
        elif isinstance(order, Core):
            self._draw_core(order)
        elif isinstance(order, Move):
            self._draw_move(order)
        elif isinstance(order, ConvoyMove):
            self._draw_move(order)
        elif isinstance(order, Support):
            self._draw_support(order)
        elif isinstance(order, ConvoyTransport):
            self._draw_convoy(order)
        elif isinstance(order, RetreatMove):
            self._draw_move(order)
        elif isinstance(order, RetreatDisband):
            self._draw_disband(order)
        elif isinstance(order, Build):
            self._draw_build(order)
        elif isinstance(order, Disband):
            self._draw_disband(order)
        else:
            raise RuntimeError(f"Unknown order type: {order.__class__}")

    def _update_provinces_and_centers(self) -> None:
        for province in self.board.provinces:
            # TODO: (MAP) implement
            #  find svg province element, edit fill color (land x1, island x2, sea x0) read off of province
            #  find svg center element, edit core and half-core fill colors read off of province
            pass

    def _update_units(self) -> None:
        units = self.board.units.copy()
        # TODO: (MAP) implement
        #  loop over svg unit elements:
        #    delete those that are not in a province that has a unit
        #    edit the rest: province label & position taking into account transforms, removing unit from units
        #  add new svg element for each remaining unit
        pass


def _create_element(tag: str, attributes: dict[str, any]) -> etree.Element:
    attributes_str = {key: str(val) for key, val in attributes.items()}
    return etree.Element(tag, attributes_str)
