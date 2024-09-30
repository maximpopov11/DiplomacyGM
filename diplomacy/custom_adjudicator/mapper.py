import copy
import itertools
import math
import re
import sys
import numpy as np
from xml.etree.ElementTree import ElementTree, Element

from lxml import etree

from diplomacy.map_parser.vector.config_svg import (
    SVG_PATH,
    UNITS_LAYER_ID,
    STROKE_WIDTH,
    RADIUS,
    PHANTOM_PRIMARY_ARMY_LAYER_ID,
    PHANTOM_PRIMARY_FLEET_LAYER_ID,
    LAND_PROVINCE_LAYER_ID,
    ISLAND_FILL_LAYER_ID,
    NEUTRAL_PROVINCE_COLOR,
    SUPPLY_CENTER_LAYER_ID,
    ISLAND_RING_LAYER_ID,
    SEASON_TITLE_LAYER_ID
)
from diplomacy.map_parser.vector.utils import get_svg_element, get_unit_coordinates
from diplomacy.persistence.board import Board
from diplomacy.persistence.db.database import logger
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
    PlayerOrder,
)
from diplomacy.persistence.phase import Phase, is_builds_phase, is_retreats_phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import ProvinceType, Province, Coast
from diplomacy.persistence.unit import Unit, UnitType

from diplomacy.custom_adjudicator.defs import (
    AdjudicableOrder
)


# TODO: (QOL) decrease line length by arrowhead (if applicable) and unit radius to match up to edge of hold circle
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
    ball_marker: Element = _create_element(
        "marker",
        {
            "id": "ball",
            "viewbox": "0 0 3 3",
            #"refX": "1.5",
            #"refY": "1.5",
            "markerWidth": "3",
            "markerHeight": "3",
            "orient": "auto-start-reverse",
        },
    )
    ball_def: Element = _create_element(
        "circle",
        {
            "r": "2",
            "fill": "black"
        },
    )
    ball_marker.append(ball_def)
    defs.append(ball_marker)



# move this function somewhere more appropriate?
def color_element(element: Element, color: str, key="fill"):
    if len(color) == 6:  # Potentially buggy hack; just assume everything with length 6 is rgb without #
        color = f"#{color}"
    if element.get(key) is not None:
        element.set(key, color)
    if element.get("style") is not None and key in element.get("style"):
        style = element.get("style")
        style = re.sub(key + r":#[0-9a-fA-F]{6}", f"{key}:{color}", style)
        element.set("style", style)


# TODO: (!) we don't draw half cores
class Mapper:
    def __init__(self, board: Board):
        self.board: Board = board
        self.board_svg: ElementTree = etree.parse(SVG_PATH)

        _add_arrow_definition_to_svg(self.board_svg)

        units_layer: Element = get_svg_element(self.board_svg, UNITS_LAYER_ID)
        self.board_svg.getroot().remove(units_layer)

        # TODO: Switch to passing the SVG directly, as that's simpiler (self.svg = draw_units(svg)?)
        self._draw_units()
        self._color_provinces()
        self._color_centers()
        self.draw_side_panel(self.board_svg)

        self._moves_svg = copy.deepcopy(self.board_svg)

        self.state_svg = copy.deepcopy(self.board_svg)
        
        self.highlight_retreating_units(self.state_svg)

    # TODO: (!) manually assert all phantom coordinates on provinces and coasts are set, fix if not
    # TODO: (BETA) print svg moves & results files in Discord GM channel
    # TODO: (DB) let's not have a ton of old files: delete moves & results after output (or don't store at all?)
    def draw_moves_map(self, phase: Phase, player_restriction: Player | None) -> str:
        self._reset_moves_map()

        if not is_builds_phase(phase):
            for unit in self.board.units:
                if player_restriction and unit.player != player_restriction:
                    continue
                if is_retreats_phase(phase) and unit.province.dislodged_unit != unit:
                    continue
                
                if is_retreats_phase(phase):
                    coordinate = unit.province.retreat_unit_coordinate
                else:
                    coordinate = unit.province.primary_unit_coordinate

                try:
                    self._draw_order(unit, coordinate)
                except Exception as err:
                    logger.error(f"Drawing move failed for {unit}", exc_info=err)
        else:
            players: set[Player]
            if player_restriction is None:
                players = self.board.players
            else:
                players = {player_restriction}
            for player in players:
                for build_order in player.build_orders:
                    self._draw_player_order(player, build_order)

        self.draw_side_panel(self._moves_svg)
        svg_file_name = f"{self.board.phase.name}_moves_map.svg"
        self._moves_svg.write(svg_file_name)
        return svg_file_name

    def draw_current_map(self) -> str:
        svg_file_name = f"{self.board.phase.name}_map.svg"
        self.state_svg.write(svg_file_name)
        return svg_file_name

    def get_pretty_date(self) -> str:
        # TODO: Get the start date from somewhere in the board/in a config file
        return self.board.phase.name + " " + str(self.board.year + 1642)

    def draw_side_panel(self, svg) -> None:
        date = get_svg_element(svg.getroot(), SEASON_TITLE_LAYER_ID)
        # TODO: this is hacky; I don't know a better way
        date[0][0].text = self.get_pretty_date()

    def _reset_moves_map(self):
        self._moves_svg = copy.deepcopy(self.board_svg)

    def _draw_order(self, unit: Unit, coordinate: tuple[float, float]) -> None:
        # TODO: (BETA) draw failed moves on adjudication (not player check) in red
        order = unit.order
        if isinstance(order, Hold):
            self._draw_hold(coordinate)
        elif isinstance(order, Core):
            self._draw_core(coordinate)
        elif isinstance(order, Move):
            adjorder = AdjudicableOrder(unit)
            if not adjorder.requires_convoy:
                self._draw_move(order, coordinate)
            else:
                self._draw_convoyed_move(unit, coordinate)
        #elif isinstance(order, ConvoyMove):
        #    self._draw_move(order, coordinate)
        elif isinstance(order, Support):
            self._draw_support(order, coordinate)
        elif isinstance(order, ConvoyTransport):
            #self._draw_convoy(order, coordinate)
            pass
        elif isinstance(order, RetreatMove):
            self._draw_move(order, coordinate)
        elif isinstance(order, RetreatDisband):
            self._draw_force_disband(coordinate, self._moves_svg)
        else:
            self._draw_hold(coordinate)
            logger.debug(f"None order found: hold drawn. Coordinates: {coordinate}")

    def _draw_player_order(self, player: Player, order: PlayerOrder):
        if order.location.primary_unit_coordinate is None:
            logger.error(f"Coordinate for {order} is invalid!")
            return
        if isinstance(order, Build):
            self._draw_build(player, order)
        elif isinstance(order, Disband):
            self._draw_force_disband(order.location.primary_unit_coordinate, self._moves_svg)
        else:
            logger.error(f"Could not draw player order {order}")

    def _draw_hold(self, coordinate: tuple[float, float]) -> None:
        element = self._moves_svg.getroot()
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
        element = self._moves_svg.getroot()
        drawn_order = _create_element(
            "rect",
            {
                "x": coordinate[0] - RADIUS,
                "y": coordinate[1] - RADIUS,
                "width": RADIUS * 2,
                "height": RADIUS * 2,
                "fill": "none",
                "stroke": "black",
                "stroke-width": STROKE_WIDTH,
                "transform": f"rotate(45 {coordinate[0]} {coordinate[1]})",
            },
        )
        element.append(drawn_order)

    def _draw_move(
        self, order: Move | ConvoyMove | RetreatMove, coordinate: tuple[float, float], use_moves_svg=True
    ) -> None:
        element = self._moves_svg.getroot() if use_moves_svg else self.board_svg.getroot()
        order_path = _create_element(
            "path",
            {
                "d": f"M {coordinate[0]},{coordinate[1]} "
                + f"   L {order.destination.primary_unit_coordinate[0]},{order.destination.primary_unit_coordinate[1]}",
                "fill": "none",
                "stroke": "red" if isinstance(order, RetreatMove) else "black",
                "stroke-width": STROKE_WIDTH,
                "marker-end": "url(#arrow)",
            },
        )
        element.append(order_path)

    def _path_helper(self, source: Province, destination: Province, current: Province, already_checked=()) -> list[tuple[Province]]:
        if current in already_checked:
            return [()]
        options = []
        new_checked = already_checked + (current,)
        for possibility in current.adjacent:
            print(f"currently in {current.name}, now checking {possibility.name}")
            if possibility == destination:
                options += [(destination,)]
            if possibility.type == ProvinceType.SEA and possibility.unit is not None and possibility.unit.unit_type == UnitType.FLEET and isinstance(possibility.unit.order, ConvoyTransport) and possibility.unit.order.source.province is source and possibility.unit.order.destination is destination:
                options += self._path_helper(source, destination, possibility, new_checked)
        return list(map((lambda t: (current,) + t), options))

    def draw_line(self, start: tuple[float, float], end: tuple[float, float], svg, marker_end="arrow", stroke_color="black"):
        element = svg.getroot()
        order_path = _create_element(
            "path",
            {
                "d": f"M {start[0]},{start[1]} "
                + f"   L {end[0]},{end[1]}",
                "fill": "none",
                "stroke": stroke_color,
                "stroke-width": STROKE_WIDTH,
                "marker-end": f"url(#{marker_end})",
            },
        )
        element.append(order_path)


    def _get_all_paths(self, unit: Unit) -> list[tuple[Province]]:
        paths = self._path_helper(unit.province, unit.order.destination, unit.province)
        if paths == [()]:
            return [(unit.province, unit.order.destination)]
        return paths
    
    #removes unnesseary convoys, for instance [A->B->C & A->C] -> [A->C]
    def get_shortest_paths(self, args: list[tuple[Province]]):
        args.sort(key=len)
        min_subsets = []
        for s in args:
            if not any(set(min_subset).issubset(s) for min_subset in min_subsets):
                min_subsets.append(s)

        return min_subsets

    def _draw_convoyed_move(self, unit: Unit, coordinate: tuple[float, float]):
        valid_convoys = self._get_all_paths(unit)
        # TODO: make this a setting
        if False:
            if len(valid_convoys):
                valid_convoys = valid_convoys[0:1]
        print(list(map((lambda m: list(map((lambda p: p.name), m))), valid_convoys)))
        # removed until we get adjacencies all figured out
        #valid_convoys = self.get_shortest_paths(valid_convoys)
        for path in valid_convoys:
            lines = zip(path[:-1], path[1:])
            for line in lines:
                self.draw_line(line[0].primary_unit_coordinate, line[1].primary_unit_coordinate, self._moves_svg, marker_end="ball")
        

    def _draw_support(self, order: Support, coordinate: tuple[float, float]) -> None:
        element = self._moves_svg.getroot()
        x1 = coordinate[0]
        y1 = coordinate[1]
        x2 = order.source.province.primary_unit_coordinate[0]
        y2 = order.source.province.primary_unit_coordinate[1]
        x3 = order.destination.primary_unit_coordinate[0]
        y3 = order.destination.primary_unit_coordinate[1]
        drawn_order = _create_element(
            "path",
            {
                "d": f"M {x1},{y1} Q {x2},{y2} {x3},{y3}",
                "fill": "none",
                "stroke": "black",
                "stroke-dasharray": "5 5",
                "stroke-width": STROKE_WIDTH,
                # FIXME: for support holds, is it source == destination? or destination is None? change if needed
                "marker-end": "url(#arrow)" if order.source.province == order.destination else "",
            },
        )
        element.append(drawn_order)

    def _draw_convoy(self, order: ConvoyTransport, coordinate: tuple[float, float]) -> None:
        element = self._moves_svg.getroot()
        x1 = order.source.province.primary_unit_coordinate[0]
        y1 = order.source.province.primary_unit_coordinate[1]

        source_angle = math.atan(
            (order.source.province.primary_unit_coordinate[1] - coordinate[1])
            / (order.source.province.primary_unit_coordinate[0] - coordinate[0])
        )
        x2 = coordinate[0] + math.cos(source_angle) * RADIUS
        y2 = coordinate[1] + math.sin(source_angle) * RADIUS

        destination_angle = math.atan(
            (order.destination.primary_unit_coordinate[1] - coordinate[1])
            / (order.destination.primary_unit_coordinate[0] - coordinate[0])
        )
        x3 = coordinate[0] + math.cos(destination_angle) * RADIUS
        y3 = coordinate[1] + math.sin(destination_angle) * RADIUS

        x4 = order.destination.primary_unit_coordinate[0]
        y4 = order.destination.primary_unit_coordinate[1]

        drawn_order = _create_element(
            "path",
            {
                "d": f"M {x1},{y1} L {x2},{y2} A {RADIUS},{RADIUS} 0 0 1 {x3},{y3} L {x4},{y4}",
                "fill": "none",
                "stroke": "black",
                "stroke-width": STROKE_WIDTH,
                "marker-end": "url(#arrow)",
            },
        )
        element.append(drawn_order)

    def _draw_build(self, player, order: Build) -> None:
        element = self._moves_svg.getroot()
        drawn_order = _create_element(
            "circle",
            {
                "cx": order.location.primary_unit_coordinate[0],
                "cy": order.location.primary_unit_coordinate[1],
                "r": 10,
                "fill": "none",
                "stroke": "green",
                "stroke-width": STROKE_WIDTH,
            },
        )

        coast = None
        province = order.location
        if isinstance(province, Coast):
            coast = province
            province = province.province
        self._draw_unit(Unit(order.unit_type, player, province, coast, None), use_moves_svg=True)
        element.append(drawn_order)

    def _draw_disband(self, coordinate: tuple[float, float], svg) -> None:
        element = svg.getroot()
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

    def _draw_force_disband(self, coordinate: tuple[float, float], svg) -> None:
        element = svg.getroot()
        cross_width = STROKE_WIDTH / (2 ** 0.5)
        square_rad = RADIUS / (2 ** 0.5)
        # two corner and a center point. Rotate and concat them to make the correct object
        init = np.array([
            (-square_rad + cross_width, -square_rad),
            (-square_rad, -square_rad + cross_width),
            (-cross_width, 0),
        ])
        rotate_90 = np.array([
            [0, -1],
            [1, 0]
        ])
        points = np.concatenate((init, init @ rotate_90, -init, -init @ rotate_90)) + coordinate
        drawn_order = _create_element(
            "polygon",
            {
                "points": ' '.join(map(lambda a:','.join(map(str, a)), points)),
                "fill": "red",
            },
        )

        element.append(drawn_order)

    def _color_provinces(self) -> None:
        province_layer = get_svg_element(self.board_svg, LAND_PROVINCE_LAYER_ID)
        island_fill_layer = get_svg_element(self.board_svg, ISLAND_FILL_LAYER_ID)
        island_ring_layer = get_svg_element(self.board_svg, ISLAND_RING_LAYER_ID)

        visited_provinces: set[str] = set()

        for province_element in itertools.chain(province_layer, island_fill_layer):
            try:
                province = self._get_province_from_element_by_label(province_element)
            except ValueError as ex:
                print(f"Error during recoloring provinces: {ex}", file=sys.stderr)
                continue

            visited_provinces.add(province.name)
            color = NEUTRAL_PROVINCE_COLOR
            if province.owner:
                color = province.owner.color
            color_element(province_element, color)

        # Try to combine this with the code above? A lot of repeated stuff here
        for island_ring in island_ring_layer:
            try:
                province = self._get_province_from_element_by_label(island_ring)
            except ValueError as ex:
                print(f"Error during recoloring provinces: {ex}", file=sys.stderr)
                continue

            color = NEUTRAL_PROVINCE_COLOR
            if province.owner:
                color = province.owner.color
            color_element(island_ring, color, key="stroke")

        for province in self.board.provinces:
            if province.type == ProvinceType.SEA:
                continue
            if province.name in visited_provinces:
                continue
            print(f"Warning: Province {province.name} was not recolored by mapper!")

    def _color_centers(self) -> None:
        centers_layer = get_svg_element(self.board_svg, SUPPLY_CENTER_LAYER_ID)

        for center_element in centers_layer:
            try:
                province = self._get_province_from_element_by_label(center_element)
            except ValueError as ex:
                print(f"Error during recoloring centers: {ex}", file=sys.stderr)
                continue

            if not province.has_supply_center:
                print(f"Province {province.name} says it has no supply center, but it does", file=sys.stderr)
                continue

            color = "#ffffff"
            if province.core:
                color = province.core.color
            elif province.half_core:
                # TODO: I tried to put "repeating-linear-gradient(white, {province.half_core.color})" here but that
                #  doesn't work. Doing this in SVG requires making a new pattern in defs which means doing a separate
                #  pattern for every single color, which would suck
                #  https://stackoverflow.com/questions/27511153/fill-svg-element-with-a-repeating-linear-gradient-color
                # ...it doesn't have to be stripes, that was just my first idea. We could figure something else out.
                pass
            for path in center_element.getchildren():
                color_element(path, color)

    def _get_province_from_element_by_label(self, element: Element) -> Province:
        province_name = element.get("{http://www.inkscape.org/namespaces/inkscape}label")
        if province_name is None:
            raise ValueError(f"Unlabeled element {element}")
        province = self.board.get_province(province_name)
        if province is None:
            raise ValueError(f"Could not find province for label {province_name}")
        return province

    def _draw_units(self) -> None:
        for unit in self.board.units:
            self._draw_unit(unit)

    def _draw_unit(self, unit: Unit, use_moves_svg=False):
        unit_element = self._get_element_for_unit_type(unit.unit_type)

        for path in unit_element.getchildren():
            color_element(path, unit.player.color)

        current_coords = get_unit_coordinates(unit_element)

        desired_province = unit.province
        if unit.coast:
            desired_province = unit.coast

        desired_coords = desired_province.primary_unit_coordinate
        if unit == unit.province.dislodged_unit:
            desired_coords = desired_province.retreat_unit_coordinate

        unit_element.set(
            "transform", f"translate({desired_coords[0] - current_coords[0]},{desired_coords[1] - current_coords[1]})"
        )
        unit_element.set("id", unit.province.name)
        unit_element.set("{http://www.inkscape.org/namespaces/inkscape}label", unit.province.name)

        root_element = self.board_svg.getroot() if not use_moves_svg else self._moves_svg.getroot()
        root_element.append(unit_element)

    def highlight_retreating_units(self, svg):
        for unit in self.board.units:
            if unit == unit.province.dislodged_unit:
                self._draw_retreat_options(unit, svg)

    def _get_element_for_unit_type(self, unit_type) -> Element:
        # Just copy a random phantom unit
        if unit_type == UnitType.ARMY:
            layer: Element = get_svg_element(self.board_svg, PHANTOM_PRIMARY_ARMY_LAYER_ID)
        else:
            layer: Element = get_svg_element(self.board_svg, PHANTOM_PRIMARY_FLEET_LAYER_ID)
        return copy.deepcopy(layer.getchildren()[0])

    def _draw_retreat_options(self, unit: Unit, svg):
        #if not unit.retreat_options:
        #    self._draw_force_disband(unit.province.retreat_unit_coordinate, svg)
        #else:
        self._draw_disband(unit.province.retreat_unit_coordinate, svg)
        # for retreat_province in unit.retreat_options:
        #     self._draw_move(RetreatMove(retreat_province), unit.province.retreat_unit_coordinate, use_moves_svg=False)


def _create_element(tag: str, attributes: dict[str, any]) -> etree.Element:
    attributes_str = {key: str(val) for key, val in attributes.items()}
    return etree.Element(tag, attributes_str)
