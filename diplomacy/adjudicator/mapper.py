from xml.etree.ElementTree import ElementTree, Element

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


def _add_arrow_definition_to_svg(svg: ElementTree) -> None:
    defs: Element = svg.find("{http://www.w3.org/2000/svg}defs")
    if defs is None:
        defs = _create_element("defs", {})
        svg.getroot().append(defs)
    # TODO: Check if 'arrow' id is already defined in defs
    arrow_marker: Element = _create_element(
        "marker",
        {
            "id": "arrow",
            "viewbox": "0 0 3 3",
            "refX": "1.5",
            "refY": "1.5",
            "markerWidth": "3",
            "markerHeight": "3",
            "orient": "auto-start-reverse",
        },
    )
    arrow_path: Element = _create_element(
        "path",
        {"d": "M 0,0 L 3,1.5 L 0,3 z"},
    )
    arrow_marker.append(arrow_path)
    defs.append(arrow_marker)


class Mapper:
    def __init__(self, board: Board):
        self.board: Board = board
        self.moves_svg: ElementTree = etree.parse(SVG_PATH)
        self.results_svg: ElementTree = etree.parse(SVG_PATH)

        _add_arrow_definition_to_svg(self.moves_svg)
        _add_arrow_definition_to_svg(self.results_svg)

    # TODO: (MAP) manually assert all phantom coordinates on provinces and coasts are set
    # TODO: (BETA) print svg moves & results files in Discord GM channel
    # TODO: (DB) let's not have a ton of old files: delete moves & results after output (or don't store at all?)
    def draw_moves_map(self, player_restriction: Player | None) -> None:
        # TODO: (MAP) current not getting player orders, get that from board (maybe get all orders at once?)
        for unit in self.board.units:
            if player_restriction and unit.player != player_restriction:
                continue

            coordinate = unit.get_coordinate()
            self._draw_order(unit.order, coordinate)
        self.moves_svg.write("moves_map.svg")

    def draw_results_map(self) -> None:
        # TODO: (MAP) get state dif or calculate state diff?
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
        mid_point = (
            (coordinate[0] + order.destination.primary_unit_coordinate[0]) / 2,
            (coordinate[1] + order.destination.primary_unit_coordinate[1]) / 2,
        )
        x_diff = coordinate[0] - order.destination.primary_unit_coordinate[0]
        y_diff = coordinate[1] - order.destination.primary_unit_coordinate[1]
        CURVINESS = 0.5  # TODO - move to config
        # A point lying on the perpendicular bisector of the line that the path should curve toward
        control_point = (
            mid_point[0] - (y_diff * CURVINESS),
            mid_point[1] - (x_diff * CURVINESS),
        )
        order_path = _create_element(
            "path",
            {
                "d": f"M {coordinate[0]},{coordinate[1]} "
                + f"Q {control_point[0]},{control_point[1]} "
                + f"  {order.destination.primary_unit_coordinate[0]},{order.destination.primary_unit_coordinate[1]}",
                "fill": "none",
                "stroke": "red" if isinstance(order, RetreatMove) else "black",
                "stroke-width": STROKE_WIDTH,
                "marker-end": "url(#arrow)",
            },
        )
        element.append(order_path)

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
