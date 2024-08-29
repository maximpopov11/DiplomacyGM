from xml.etree.ElementTree import ElementTree

from lxml import etree

from diplomacy.map_parser.vector.config_svg import SVG_PATH, STROKE_WIDTH, RADIUS
from diplomacy.persistence.board import Board
from diplomacy.persistence.order import (
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
    Order,
)
from diplomacy.persistence.player import Player


class Mapper:
    def __init__(self, board: Board):
        self.board: Board = board
        self.moves_svg: ElementTree = etree.parse(SVG_PATH)
        self.results_svg: ElementTree = etree.parse(SVG_PATH)

    # TODO: (BETA) print svg moves & results files in Discord GM channel
    # TODO: (DB) let's not have a ton of old files: delete moves & results after output (or don't store at all?)
    def get_moves_map(self, player_restriction: Player | None) -> None:
        for unit in self.board.units:
            if player_restriction and unit.player != player_restriction:
                continue

            coordinate = unit.get_coordinate()
            self._draw_order(unit.order, coordinate)
        self.moves_svg.write("moves_map.svg")

    def get_results_map(self) -> None:
        self._update_units()
        self._update_provinces_and_centers()
        self.moves_svg.write("results_map.svg")

    def _draw_order(self, order: Order, coordinate: tuple[float, float]) -> None:
        # TODO: (BETA) draw failed moves on adjudication (not player check) in red
        # TODO: (MAP) draw arrowhead for move, convoy, support
        if isinstance(order, Hold):
            self._draw_hold(coordinate)
        elif isinstance(order, Core):
            self._draw_core(coordinate)
        elif isinstance(order, Move):
            self._draw_move(order, coordinate)
        elif isinstance(order, ConvoyMove):
            self._draw_move(order, coordinate)
        elif isinstance(order, Support):
            self._draw_support(order, coordinate)
        elif isinstance(order, ConvoyTransport):
            self._draw_convoy(order, coordinate)
        elif isinstance(order, RetreatMove):
            self._draw_move(order, coordinate)
        elif isinstance(order, RetreatDisband):
            self._draw_disband(coordinate)
        elif isinstance(order, Build):
            self._draw_build(order)
        elif isinstance(order, Disband):
            self._draw_disband(coordinate)
        else:
            raise RuntimeError(f"Unknown order type: {order.__class__}")

    def _draw_hold(self, coordinate: tuple[float, float]) -> None:
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
            "circle",
            {
                "cx": coordinate[0],
                "cy": coordinate[1],
                "r": RADIUS,
                "fill": "none",
                "stroke": "black",
                "stroke-width": STROKE_WIDTH,
            },
        )
        element.append(drawn_order)

    def _draw_core(self, coordinate: tuple[float, float]) -> None:
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
            "rect",
            {
                "x": coordinate[0] - RADIUS,
                "y": coordinate[1] - RADIUS,
                "width": RADIUS + RADIUS * 1.2 * 2,
                "height": RADIUS + RADIUS * 1.2 * 2,
                "fill": "none",
                "stroke": "green",
                "stroke-width": STROKE_WIDTH,
                "transform": "rotate(45 100 100)",
            },
        )
        element.append(drawn_order)

    def _draw_move(self, order: Move | ConvoyMove | RetreatMove, coordinate: tuple[float, float]) -> None:
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
            "line",
            {
                "x1": coordinate[0],
                "y1": coordinate[1],
                "x2": order.destination.primary_unit_coordinate[0],
                "y2": order.destination.primary_unit_coordinate[1],
                "fill": "none",
                "stroke": "black",
                "stroke-width": STROKE_WIDTH,
            },
        )
        element.append(drawn_order)

    def _draw_support(self, order: Support, coordinate: tuple[float, float]) -> None:
        element = self.moves_svg.getroot()
        x1 = coordinate[0]
        y1 = coordinate[1]
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
                "stroke-width": STROKE_WIDTH,
            },
        )
        element.append(drawn_order)

    def _draw_convoy(self, order: ConvoyTransport, coordinate: tuple[float, float]) -> None:
        element = self.moves_svg.getroot()
        x1 = order.source.province.primary_unit_coordinate[0]
        y1 = order.source.province.primary_unit_coordinate[1]
        x2 = coordinate[0]
        y2 = coordinate[1]
        x3 = order.destination.primary_unit_coordinate[0]
        y3 = order.destination.primary_unit_coordinate[1]
        path = f"M {x1},{y1} {x2},{y2} {x3},{y3}"
        drawn_order = _create_element(
            "path",
            {
                "d": path,
                "fill": "none",
                "stroke": "black",
                "stroke-width": STROKE_WIDTH,
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
                "stroke-width": STROKE_WIDTH,
            },
        )
        element.append(drawn_order)

    def _draw_disband(self, coordinate: tuple[float, float]) -> None:
        element = self.moves_svg.getroot()
        drawn_order = _create_element(
            "circle",
            {
                "cx": coordinate[0],
                "cy": coordinate[1],
                "r": RADIUS,
                "fill": "none",
                "stroke": "red",
                "stroke-width": STROKE_WIDTH,
            },
        )
        element.append(drawn_order)

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
