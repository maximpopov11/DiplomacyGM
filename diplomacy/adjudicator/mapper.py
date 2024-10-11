import copy
import itertools
import re
import sys
from xml.etree.ElementTree import ElementTree, Element

import numpy as np
from lxml import etree

from diplomacy.adjudicator.utils import (
    get_closest_loc,
    add_arrow_definition_to_svg,
    create_element,
    pull_coordinate,
    loc_to_point,
    color_element,
    normalize,
)
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
    SEASON_TITLE_LAYER_ID,
    POWER_BANNERS_LAYER_ID,
    MAP_WIDTH,
)
from diplomacy.map_parser.vector.utils import get_element_color, get_svg_element, get_unit_coordinates
from diplomacy.persistence import phase
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
    PlayerOrder,
)
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import ProvinceType, Province, Coast, Location
from diplomacy.persistence.unit import Unit, UnitType

OUTPUTLAYER = "layer16"
UNITLAYER = "layer17"


class Mapper:
    def __init__(self, board: Board):
        self.board: Board = board
        self.board_svg: ElementTree = etree.parse(SVG_PATH)
        self.player_restriction: Player | None = None
        self._initialize_scoreboard_locations()

        add_arrow_definition_to_svg(self.board_svg)

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

    def draw_moves_map(self, current_phase: phase.Phase, player_restriction: Player | None) -> str:
        self._reset_moves_map()
        self.player_restriction = player_restriction
        if not phase.is_builds(current_phase):
            for unit in self.board.units:
                if player_restriction and unit.player != player_restriction:
                    continue
                if phase.is_retreats(current_phase) and unit.province.dislodged_unit != unit:
                    continue

                if phase.is_retreats(current_phase):
                    unit_locs = unit.get_location().all_rets
                else:
                    unit_locs = unit.get_location().all_locs

                # TODO: Maybe there's a better way to handle convoys?
                if isinstance(unit.order, (RetreatMove, Move, Support)):
                    new_locs = []
                    for endpoint in unit.order.destination.all_locs:
                        new_locs += [normalize(get_closest_loc(unit_locs, endpoint))]
                    unit_locs = new_locs
                try:
                    for loc in unit_locs:
                        val = self._draw_order(unit, loc)
                        if val is not None:
                            # if something returns, that means it could potentially go across the edge
                            # copy it 3 times (-1, 0, +1)
                            lval = copy.deepcopy(val)
                            rval = copy.deepcopy(val)
                            lval.attrib["transform"] = f"translate({-MAP_WIDTH}, 0)"
                            rval.attrib["transform"] = f"translate({MAP_WIDTH}, 0)"
                            t = self._moves_svg.getroot()

                            l = get_svg_element(t, OUTPUTLAYER)

                            l.append(lval)
                            l.append(rval)
                            l.append(val)
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

    def draw_side_panel(self, svg: ElementTree) -> None:
        self._draw_side_panel_date(svg)
        self._draw_side_panel_scoreboard(svg)

    def _draw_side_panel_scoreboard(self, svg: ElementTree) -> None:
        '''
        format is a list of each power; for each power, its children nodes are as follows:
        0: colored rectangle
        1: full name ("Dutch Empire", ...)
        2-4: "current", "victory", "start" text labels in that order
        5-7: SC counts in that same order
        '''
        all_power_banners_element = get_svg_element(svg.getroot(), POWER_BANNERS_LAYER_ID)
        for (i, player) in enumerate(self.board.get_players_sorted_by_vscc()):
            for power_element in all_power_banners_element:
                # match the correct svg element based on the color of the rectangle
                if get_element_color(power_element[0]) == player.color:
                    power_element.set('transform', self.scoreboard_power_locations[i])
                    power_element[5][0].text = str(len(player.centers))
                    break
    
    def _draw_side_panel_date(self, svg: ElementTree) -> None:
        date = get_svg_element(svg.getroot(), SEASON_TITLE_LAYER_ID)
        # TODO: this is hacky; I don't know a better way
        date[0][0].text = self.get_pretty_date()

    def _reset_moves_map(self):
        self._moves_svg = copy.deepcopy(self.board_svg)

    def _draw_order(self, unit: Unit, coordinate: tuple[float, float]) -> None:
        order = unit.order
        if isinstance(order, Hold):
            self._draw_hold(coordinate)
        elif isinstance(order, Core):
            self._draw_core(coordinate)
        elif isinstance(order, Move):
            # moves are just convoyed moves that have no convoys
            return self._draw_convoyed_move(unit, coordinate)
        elif isinstance(order, ConvoyMove):
            logger.warning("Convoy move is depricated; use move instead")
            return self._draw_convoyed_move(unit, coordinate)
        elif isinstance(order, Support):
            return self._draw_support(unit, coordinate)
        elif isinstance(order, ConvoyTransport):
            self._draw_convoy(order, coordinate)
        elif isinstance(order, RetreatMove):
            return self._draw_retreat_move(order, coordinate)
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
            for coord in order.location.all_locs:
                self._draw_force_disband(coord, self._moves_svg)
        else:
            logger.error(f"Could not draw player order {order}")

    def _draw_hold(self, coordinate: tuple[float, float]) -> None:
        element = self._moves_svg.getroot()
        drawn_order = create_element(
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
        drawn_order = create_element(
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

    def _draw_retreat_move(self, order: RetreatMove, coordinate: tuple[float, float], use_moves_svg=True) -> None:
        destination = loc_to_point(order.destination, coordinate)
        if order.destination.get_unit():
            destination = pull_coordinate(coordinate, destination)
        order_path = create_element(
            "path",
            {
                "d": f"M {coordinate[0]},{coordinate[1]} L {destination[0]},{destination[1]}",
                "fill": "none",
                "stroke": "red",
                "stroke-width": STROKE_WIDTH,
                "stroke-linecap": "round",
                "marker-end": "url(#arrow)",
            },
        )
        return order_path

    def _path_helper(
        self, source: Province, destination: Province, current: Province, already_checked=()
    ) -> list[tuple[Province]]:
        if current in already_checked:
            return []
        options = []
        new_checked = already_checked + (current,)
        for possibility in current.adjacent:
            if possibility == destination:
                return [
                    (
                        current.get_unit().get_location(),
                        destination,
                    )
                ]
            if (
                possibility.type == ProvinceType.SEA
                and possibility.unit is not None
                and (self.player_restriction is None or possibility.unit.player == self.player_restriction)
                and possibility.unit.unit_type == UnitType.FLEET
                and isinstance(possibility.unit.order, ConvoyTransport)
                and possibility.unit.order.source.province is source
                and possibility.unit.order.destination is destination
            ):
                options += self._path_helper(source, destination, possibility, new_checked)
        return list(map((lambda t: (current.get_unit().get_location(),) + t), options))

    def _draw_path(self, d: str, marker_end="arrow", stroke_color="black"):
        order_path = create_element(
            "path",
            {
                "d": d,
                "fill": "none",
                "stroke": stroke_color,
                "stroke-width": STROKE_WIDTH,
                "stroke-linecap": "round",
                "marker-end": f"url(#{marker_end})",
            },
        )
        return order_path

    def _get_all_paths(self, unit: Unit) -> list[tuple[Province]]:
        paths = self._path_helper(unit.province, unit.order.destination, unit.province)
        if paths == []:
            return [(unit.province, unit.order.destination)]
        return paths

    # removes unnesseary convoys, for instance [A->B->C & A->C] -> [A->C]
    def get_shortest_paths(self, args: list[tuple[Province]]) -> list[tuple[Location]]:
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
        valid_convoys = self.get_shortest_paths(valid_convoys)
        for path in valid_convoys:
            p = [coordinate]
            start = coordinate
            for loc in path[1:]:
                p += [loc_to_point(loc, start)]
                start = p[-1]

            if path[-1].get_unit():
                p[-1] = pull_coordinate(p[-2], p[-1])

            p = np.array(p)

            def f(point: tuple[float, float]):
                return " ".join(map(str, point))

            def norm(point: tuple[float, float]) -> tuple[float, float]:
                return point / ((np.sum(point**2)) ** 0.5)

            # given surrounding points, generate a control point
            def g(point: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]):
                centered = point[::2] - point[1]

                # TODO: possible div / 0 if the two convoyed points are in a straight line with the convoyer on one side
                vec = norm(centered[0]) - norm(centered[1])
                return norm(vec) * 30 + point[1]

            # this is a bit wierd, because the loop is in-between two values
            # (S LO)(OP LO)(OP E)
            s = f"M {f(p[0])} C {f(p[1])}, "
            for x in range(1, len(p) - 1):
                s += f"{f(g(p[x-1:x+2]))}, {f(p[x])} S "

            s += f"{f(p[-2])}, {f(p[-1])}"
            return self._draw_path(s)

    def _draw_support(self, unit: Unit, coordinate: tuple[float, float]) -> None:
        order: Support = unit.order
        x1 = coordinate[0]
        y1 = coordinate[1]
        v2 = loc_to_point(order.source.get_location(), coordinate)
        x2, y2 = v2
        v3 = loc_to_point(order.destination, v2)
        x3, y3 = v3
        marker_start = ""
        if order.destination.get_unit():
            if order.source.get_location() == order.destination:
                (x3, y3) = pull_coordinate((x1, y1), (x3, y3), RADIUS)
            else:
                (x3, y3) = pull_coordinate((x2, y2), (x3, y3))
            if isinstance(order.destination.get_unit().order, (ConvoyTransport, Support)):
                for coord in order.destination.all_locs:
                    self._draw_hold(coord)
            # if two units are support-holding each other
            destorder = order.destination.get_unit().order

            if (
                isinstance(order.destination.get_unit().order, Support)
                and destorder.source.get_location() == destorder.destination == unit.get_location()
                and order.source.get_location() == order.destination
            ):
                # This check is so we only do it once, so it doesn't overlay
                # it doesn't matter which one is the origin & which is the dest
                if id(order.destination.get_unit()) > id(unit):
                    marker_start = "url(#ball)"
                    # doesn't matter that v3 has been pulled, as it's still collinear
                    (x1, y1) = (x2, y2) = pull_coordinate((x3, y3), (x1, y1), RADIUS)
                else:
                    return
        drawn_order = create_element(
            "path",
            {
                "d": f"M {x1},{y1} Q {x2},{y2} {x3},{y3}",
                "fill": "none",
                "stroke": "black",
                "stroke-dasharray": "5 5",
                "stroke-width": STROKE_WIDTH,
                "stroke-linecap": "round",
                "marker-start": marker_start,
                "marker-end": f"url(#{'ball' if order.source.get_location() == order.destination else 'arrow'})",
            },
        )
        return drawn_order

    def _draw_convoy(self, order: ConvoyTransport, coordinate: tuple[float, float]) -> None:
        element = self._moves_svg.getroot()
        drawn_order = create_element(
            "circle",
            {
                "cx": coordinate[0],
                "cy": coordinate[1],
                "r": RADIUS / 2,
                "fill": "none",
                "stroke": "black",
                "stroke-width": STROKE_WIDTH * 2 / 3,
            },
        )
        element.append(drawn_order)

    def _draw_build(self, player, order: Build) -> None:
        element = self._moves_svg.getroot()
        drawn_order = create_element(
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
        drawn_order = create_element(
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
        cross_width = STROKE_WIDTH / (2**0.5)
        square_rad = RADIUS / (2**0.5)
        # two corner and a center point. Rotate and concat them to make the correct object
        init = np.array(
            [
                (-square_rad + cross_width, -square_rad),
                (-square_rad, -square_rad + cross_width),
                (-cross_width, 0),
            ]
        )
        rotate_90 = np.array([[0, -1], [1, 0]])
        points = np.concatenate((init, init @ rotate_90, -init, -init @ rotate_90)) + coordinate
        drawn_order = create_element(
            "polygon",
            {
                "points": " ".join(map(lambda a: ",".join(map(str, a)), points)),
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

        if unit == unit.province.dislodged_unit:
            coord_list = unit.get_location().all_rets
        else:
            coord_list = unit.get_location().all_locs
        for desired_coords in coord_list:
            elem = copy.deepcopy(unit_element)
            elem.set(
                "transform",
                f"translate({desired_coords[0] - current_coords[0]},{desired_coords[1] - current_coords[1]})",
            )
            elem.set("id", unit.province.name)
            elem.set("{http://www.inkscape.org/namespaces/inkscape}label", unit.province.name)

            tree = self.board_svg if not use_moves_svg else self._moves_svg
            group = get_svg_element(tree, UNITLAYER)
            group.append(elem)

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
        # if not unit.retreat_options:
        #    self._draw_force_disband(unit.province.retreat_unit_coordinate, svg)
        # else:
        self._draw_disband(unit.province.retreat_unit_coordinate, svg)
        # for retreat_province in unit.retreat_options:
        #     self._draw_retreat_move(RetreatMove(retreat_province), unit.province.retreat_unit_coordinate, use_moves_svg=False)

    def _initialize_scoreboard_locations(self) -> None:
        all_power_banners_element = get_svg_element(svg.getroot(), POWER_BANNERS_LAYER_ID)
        self.scoreboard_power_locations : list[str] = []
        for power_element in all_power_banners_element:
            self.scoreboard_power_locations.append(power_element.get('transform'))
        
        # each power is placed in the right spot based on the transform field which has value of "tranlate($x,$y)" where x,y 
        # are floating point numbers; we parse these via regex and sort by y-value
        self.scoreboard_power_locations.sort(
            lambda loc: float(re.match(r'translate\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)', x).groups()[1])
        )
