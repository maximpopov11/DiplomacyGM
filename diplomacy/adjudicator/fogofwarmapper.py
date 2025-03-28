import copy
import itertools
import re
import sys
from xml.etree.ElementTree import ElementTree, Element, register_namespace
from xml.etree.ElementTree import tostring as elementToString

import numpy as np
from lxml import etree
import math

# from diplomacy.adjudicator import utils
# from diplomacy.map_parser.vector import config_svg as svgcfg

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

from diplomacy.map_parser.vector.transform import get_transform, MatrixTransform, Translation

# OUTPUTLAYER = "layer16"
# UNITLAYER = "layer17"


class FOWMapper:
    def __init__(self, board: Board, restriction: Player):
        register_namespace('', "http://www.w3.org/2000/svg")
        register_namespace('inkscape', "http://www.inkscape.org/namespaces/inkscape")
        register_namespace('sodipodi', "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")
        register_namespace('xlink', "http://www.w3.org/1999/xlink")
        
        self.board: Board = board
        self.board_svg: ElementTree = etree.parse(self.board.data["file"])
        self.player_restriction: Player | None = None
        self._initialize_scoreboard_locations()

        self.add_arrow_definition_to_svg(self.board_svg)

        units_layer: Element = get_svg_element(self.board_svg, self.board.data["svg config"]["starting_units"])
        units_layer.clear()

        self.cached_elements = {}
        for element_name in ["army", "fleet", "retreat_army", "retreat_fleet", "unit_output"]:
            self.cached_elements[element_name] = get_svg_element(
                self.board_svg, self.board.data["svg config"][element_name]
            )

        self.restriction = restriction
        if restriction != None:
            self.adjacent_provinces: set[Province] = self.board.get_visible_provinces(restriction)
        else:
            self.adjacent_provinces: set[Province] = self.board.provinces

        # TODO: Switch to passing the SVG directly, as that's simpiler (self.svg = draw_units(svg)?)
        self._draw_units()
        self._color_provinces()
        self._color_centers()
        self.draw_side_panel(self.board_svg)
        
        for element_name in ["retreat_army", "retreat_fleet"]:
            get_svg_element(self.board_svg, self.board.data["svg config"][element_name]).clear()

        self._moves_svg = copy.deepcopy(self.board_svg)
        self.cached_elements["unit_output_moves"] = get_svg_element(
            self._moves_svg, self.board.data["svg config"]["unit_output"]
        )

        self.state_svg = copy.deepcopy(self.board_svg)
        for element_name in ["army", "fleet"]:
            get_svg_element(self.state_svg, self.board.data["svg config"][element_name]).clear()

        self.highlight_retreating_units(self.state_svg)

    def draw_moves_map(self, current_phase: phase.Phase, player_restriction: Player | None) -> tuple[str, str]:
        logger.info("mapper.draw_moves_map")

        self._reset_moves_map()
        self.player_restriction = player_restriction
        
        t = self._moves_svg.getroot()
        arrow_layer = get_svg_element(t, self.board.data["svg config"]["arrow_output"])
        if not phase.is_builds(current_phase):
            for unit in self.board.units:
                if unit.province not in self.adjacent_provinces:
                    continue

                if player_restriction and unit.player != player_restriction:
                    continue
                if phase.is_retreats(current_phase) and unit.province.dislodged_unit != unit:
                    continue

                if phase.is_retreats(current_phase):
                    unit_locs = unit.location().all_rets
                else:
                    unit_locs = unit.location().all_locs

                # TODO: Maybe there's a better way to handle convoys?
                if isinstance(unit.order, (RetreatMove, Move, Support)):
                    new_locs = []
                    for endpoint in unit.order.destination.all_locs:
                        new_locs += [self.normalize(self.get_closest_loc(unit_locs, endpoint))]
                    unit_locs = new_locs
                try:
                    for loc in unit_locs:
                        val = self._draw_order(unit, loc, current_phase)
                        if val is not None:
                            # if something returns, that means it could potentially go across the edge
                            # copy it 3 times (-1, 0, +1)
                            lval = copy.deepcopy(val)
                            rval = copy.deepcopy(val)
                            lval.attrib["transform"] = f"translate({-self.board.data['svg config']['map_width']}, 0)"
                            rval.attrib["transform"] = f"translate({self.board.data['svg config']['map_width']}, 0)"

                            arrow_layer.append(lval)
                            arrow_layer.append(rval)
                            arrow_layer.append(val)
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
                    if build_order.location.as_province() in self.adjacent_provinces:
                        self._draw_player_order(player, build_order)

        self.draw_side_panel(self._moves_svg)
        
        svg_file_name = f"{self.board.phase.name}_{self.board.year + 1642}_moves_map.svg"
        return elementToString(self._moves_svg.getroot(), encoding="utf-8"), svg_file_name

    def draw_current_map(self) -> tuple[str, str]:
        logger.info("mapper.draw_current_map")
        svg_file_name = f"{self.board.phase.name}_{self.board.year + 1642}_map.svg"
        return elementToString(self.state_svg.getroot(), encoding="utf-8"), svg_file_name

    def get_pretty_date(self) -> str:
        # TODO: Get the start date from somewhere in the board/in a config file
        return self.board.phase.name + " " + str(self.board.year + 1642)

    def draw_side_panel(self, svg: ElementTree) -> None:
        self._draw_side_panel_date(svg)
        self._draw_side_panel_scoreboard(svg)

    def _draw_side_panel_scoreboard(self, svg: ElementTree) -> None:
        """
        format is a list of each power; for each power, its children nodes are as follows:
        0: colored rectangle
        1: full name ("Dutch Empire", ...)
        2-4: "current", "victory", "start" text labels in that order
        5-7: SC counts in that same order
        """
        all_power_banners_element = get_svg_element(svg.getroot(), self.board.data["svg config"]["power_banners"])
        for i, player in enumerate(self.board.get_players_by_score()):
            for power_element in all_power_banners_element:
                # match the correct svg element based on the color of the rectangle
                if get_element_color(power_element[0]) == player.color:
                    power_element.set("transform", self.scoreboard_power_locations[i])
                    if player == self.restriction or self.restriction == None:
                        power_element[5][0].text = str(len(player.centers))
                    else:
                        power_element[5][0].text = "???"
                    break

    def _draw_side_panel_date(self, svg: ElementTree) -> None:
        date = get_svg_element(svg.getroot(), self.board.data["svg config"]["season"])
        # TODO: this is hacky; I don't know a better way
        date[0][0].text = self.get_pretty_date()

    def _reset_moves_map(self):
        self._moves_svg = copy.deepcopy(self.board_svg)

    def _draw_order(self, unit: Unit, coordinate: tuple[float, float], current_phase: phase.Phase) -> None:
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
            if phase.is_moves(current_phase):
                self._draw_hold(coordinate)
            else:
                self._draw_force_disband(coordinate, self._moves_svg)
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
        drawn_order = self.create_element(
            "circle",
            {
                "cx": coordinate[0],
                "cy": coordinate[1],
                "r": self.board.data["svg config"]["unit_radius"],
                "fill": "none",
                "stroke": "black",
                "stroke-width": self.board.data["svg config"]["order_stroke_width"],
            },
        )
        element.append(drawn_order)

    def _draw_core(self, coordinate: tuple[float, float]) -> None:
        element = self._moves_svg.getroot()
        drawn_order = self.create_element(
            "rect",
            {
                "x": coordinate[0] - self.board.data["svg config"]["unit_radius"],
                "y": coordinate[1] - self.board.data["svg config"]["unit_radius"],
                "width": self.board.data["svg config"]["unit_radius"] * 2,
                "height": self.board.data["svg config"]["unit_radius"] * 2,
                "fill": "none",
                "stroke": "black",
                "stroke-width": self.board.data["svg config"]["order_stroke_width"],
                "transform": f"rotate(45 {coordinate[0]} {coordinate[1]})",
            },
        )
        element.append(drawn_order)

    def _draw_retreat_move(self, order: RetreatMove, coordinate: tuple[float, float], use_moves_svg=True) -> None:
        destination = self.loc_to_point(order.destination, coordinate)
        if order.destination.get_unit():
            destination = self.pull_coordinate(coordinate, destination)
        order_path = self.create_element(
            "path",
            {
                "d": f"M {coordinate[0]},{coordinate[1]} L {destination[0]},{destination[1]}",
                "fill": "none",
                "stroke": "red",
                "stroke-width": self.board.data["svg config"]["order_stroke_width"],
                "stroke-linecap": "round",
                "marker-end": "url(#redarrow)",
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
            if possibility not in self.adjacent_provinces:
                continue

            if possibility == destination:
                return [
                    (
                        current.get_unit().location(),
                        destination,
                    )
                ]
            if (
                possibility.type == ProvinceType.SEA
                and possibility.unit is not None
                and (self.player_restriction is None or possibility.unit.player == self.player_restriction)
                and possibility.unit.unit_type == UnitType.FLEET
                and isinstance(possibility.unit.order, ConvoyTransport)
                and possibility.unit.order.source.as_province() is source
                and possibility.unit.order.destination is destination
            ):
                options += self._path_helper(source, destination, possibility, new_checked)
        return list(map((lambda t: (current.get_unit().location(),) + t), options))

    def _draw_path(self, d: str, marker_end="arrow", stroke_color="black"):
        order_path = self.create_element(
            "path",
            {
                "d": d,
                "fill": "none",
                "stroke": stroke_color,
                "stroke-width": self.board.data["svg config"]["order_stroke_width"],
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
                p += [self.loc_to_point(loc, start)]
                start = p[-1]

            if path[-1].get_unit():
                p[-1] = self.pull_coordinate(p[-2], p[-1])

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
        v2 = self.loc_to_point(order.source, coordinate)
        x2, y2 = v2
        v3 = self.loc_to_point(order.destination, v2)
        x3, y3 = v3
        marker_start = ""
        if order.destination.get_unit():
            if order.source == order.destination:
                (x3, y3) = self.pull_coordinate((x1, y1), (x3, y3), self.board.data["svg config"]["unit_radius"])
            else:
                (x3, y3) = self.pull_coordinate((x2, y2), (x3, y3))
            # if isinstance(order.destination.get_unit().order, (ConvoyTransport, Support)):
            #     for coord in order.destination.all_locs:
            #         self._draw_hold(coord)
            # if two units are support-holding each other
            destorder = order.destination.get_unit().order

            if (
                isinstance(order.destination.get_unit().order, Support)
                and destorder.source == destorder.destination == unit.location()
                and order.source == order.destination
            ):
                # This check is so we only do it once, so it doesn't overlay
                # it doesn't matter which one is the origin & which is the dest
                if id(order.destination.get_unit()) > id(unit):
                    marker_start = "url(#ball)"
                    # doesn't matter that v3 has been pulled, as it's still collinear
                    (x1, y1) = (x2, y2) = self.pull_coordinate(
                        (x3, y3), (x1, y1), self.board.data["svg config"]["unit_radius"]
                    )
                else:
                    return

        dasharray_size = 2.5 * self.board.data["svg config"]["order_stroke_width"]
        drawn_order = self.create_element(
            "path",
            {
                "d": f"M {x1},{y1} Q {x2},{y2} {x3},{y3}",
                "fill": "none",
                "stroke": "black",
                "stroke-dasharray": f"{dasharray_size} {dasharray_size}",
                "stroke-width": self.board.data["svg config"]["order_stroke_width"],
                "stroke-linecap": "round",
                "marker-start": marker_start,
                "marker-end": f"url(#{'ball' if order.source == order.destination else 'arrow'})",
            },
        )
        return drawn_order

    def _draw_convoy(self, order: ConvoyTransport, coordinate: tuple[float, float]) -> None:
        element = self._moves_svg.getroot()
        drawn_order = self.create_element(
            "circle",
            {
                "cx": coordinate[0],
                "cy": coordinate[1],
                "r": self.board.data["svg config"]["unit_radius"] / 2,
                "fill": "none",
                "stroke": "black",
                "stroke-width": self.board.data["svg config"]["order_stroke_width"] * 2 / 3,
            },
        )
        element.append(drawn_order)

    def _draw_build(self, player, order: Build) -> None:
        element = self._moves_svg.getroot()
        drawn_order = self.create_element(
            "circle",
            {
                "cx": order.location.primary_unit_coordinate[0],
                "cy": order.location.primary_unit_coordinate[1],
                "r": 10,
                "fill": "none",
                "stroke": "green",
                "stroke-width": self.board.data["svg config"]["order_stroke_width"],
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
        drawn_order = self.create_element(
            "circle",
            {
                "cx": coordinate[0],
                "cy": coordinate[1],
                "r": self.board.data["svg config"]["unit_radius"],
                "fill": "none",
                "stroke": "red",
                "stroke-width": self.board.data["svg config"]["order_stroke_width"],
            },
        )
        element.append(drawn_order)

    def _draw_force_disband(self, coordinate: tuple[float, float], svg) -> None:
        element = svg.getroot()
        cross_width = self.board.data["svg config"]["order_stroke_width"] / (2**0.5)
        square_rad = self.board.data["svg config"]["unit_radius"] / (2**0.5)
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
        drawn_order = self.create_element(
            "polygon",
            {
                "points": " ".join(map(lambda a: ",".join(map(str, a)), points)),
                "fill": "red",
            },
        )

        element.append(drawn_order)

    def _color_provinces(self) -> None:
        province_layer = get_svg_element(self.board_svg, self.board.data["svg config"]["land_layer"])
        island_fill_layer = get_svg_element(self.board_svg, self.board.data["svg config"]["island_fill_layer"])
        island_ring_layer = get_svg_element(self.board_svg, self.board.data["svg config"]["island_ring_layer"])
        sea_layer = get_svg_element(self.board_svg, self.board.data["svg config"]["sea_borders"])
        island_layer = get_svg_element(self.board_svg, self.board.data["svg config"]["island_borders"])

        visited_provinces: set[str] = set()

        for province_element in itertools.chain(province_layer, island_fill_layer):
            try:
                province = self._get_province_from_element_by_label(province_element)
            except ValueError as ex:
                print(f"Error during recoloring provinces: {ex}", file=sys.stderr)
                continue

            visited_provinces.add(province.name)
            color = self.board.data["svg config"]["neutral"]
            if province not in self.adjacent_provinces:
                color = self.board.data["svg config"]["unknown"]
            elif province.owner:
                color = province.owner.color
            self.color_element(province_element, color)

        for province_element in sea_layer:
            try:
                province = self._get_province_from_element_by_label(province_element)
            except ValueError as ex:
                print(f"Error during recoloring provinces: {ex}", file=sys.stderr)
                continue

            if province in self.adjacent_provinces:
                sea_layer.remove(province_element)

            visited_provinces.add(province.name)

        for province_element in island_layer:
            try:
                province = self._get_province_from_element_by_label(province_element)
            except ValueError as ex:
                print(f"Error during recoloring provinces: {ex}", file=sys.stderr)
                continue

            if province in self.adjacent_provinces:
                island_layer.remove(province_element)

            visited_provinces.add(province.name)

        # Try to combine this with the code above? A lot of repeated stuff here
        for island_ring in island_ring_layer:
            try:
                province = self._get_province_from_element_by_label(island_ring)
            except ValueError as ex:
                print(f"Error during recoloring provinces: {ex}", file=sys.stderr)
                continue

            color = self.board.data["svg config"]["neutral"]
            if province not in self.adjacent_provinces:
                color = self.board.data["svg config"]["unknown"]
            elif province.owner:
                color = province.owner.color
            self.color_element(island_ring, color, key="stroke")

        for province in self.board.provinces:
            if province.name in visited_provinces:
                continue
            print(f"Warning: Province {province.name} was not recolored by mapper!")

    def _color_centers(self) -> None:
        centers_layer = get_svg_element(self.board_svg, self.board.data["svg config"]["supply_center_icons"])

        for center_element in centers_layer:
            try:
                province = self._get_province_from_element_by_label(center_element)
            except ValueError as ex:
                print(f"Error during recoloring centers: {ex}", file=sys.stderr)
                continue

            if not province.has_supply_center:
                print(f"Province {province.name} says it has no supply center, but it does", file=sys.stderr)
                continue

            if province not in self.adjacent_provinces:
                core_color = self.board.data["svg config"]["unknown"]
                half_color = core_color
            else:
                if province.core:
                    core_color = province.core.color
                else:
                    core_color = "#ffffff"
                if province.half_core:
                    half_color = province.half_core.color
                else:
                    half_color = core_color
            # color = "#ffffff"
            # if province.core:
            #     color = province.core.color
            # elif province.half_core:
            #     # TODO: I tried to put "repeating-linear-gradient(white, {province.half_core.color})" here but that
            #     #  doesn't work. Doing this in SVG requires making a new pattern in defs which means doing a separate
            #     #  pattern for every single color, which would suck
            #     #  https://stackoverflow.com/questions/27511153/fill-svg-element-with-a-repeating-linear-gradient-color
            #     # ...it doesn't have to be stripes, that was just my first idea. We could figure something else out.
            #     pass
            # for path in center_element.getchildren():
            #     print(f"\t{path}")
            #     self.color_element(path, color)
            for elem in center_element.getchildren():
                if elem.attrib["id"].startswith("Capital_Marker"):
                    pass
                elif "{http://www.inkscape.org/namespaces/inkscape}label" in elem.attrib and elem.attrib[
                    "{http://www.inkscape.org/namespaces/inkscape}label"
                ] in ["Halfcore Marker", "Core Marker"]:
                    # Handling capitals is easy bc it's all marked
                    # TODO: Maybe make it split vertically?
                    # that might be hard to do
                    if elem.attrib["{http://www.inkscape.org/namespaces/inkscape}label"] == "Halfcore Marker":
                        self.color_element(elem, half_color)
                    elif elem.attrib["{http://www.inkscape.org/namespaces/inkscape}label"] == "Core Marker":
                        self.color_element(elem, core_color)
                else:
                    if half_color != core_color:
                        corename = "None" if not province.core else province.core.name
                        halfname = "None" if not province.half_core else province.half_core.name
                        self.color_element(elem, f"url(#{halfname}_{corename})")
                    else:
                        self.color_element(elem, core_color)

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
            if unit.province in self.adjacent_provinces:
                self._draw_unit(unit)

    def _draw_unit(self, unit: Unit, use_moves_svg=False):
        unit_element = self._get_element_for_unit_type(unit.unit_type)

        for path in unit_element.getchildren():
            self.color_element(path, unit.player.color)

        current_coords = get_unit_coordinates(unit_element)
        current_coords = get_transform(unit_element).transform(current_coords)

        if unit == unit.province.dislodged_unit:
            coord_list = unit.location().all_rets
        else:
            coord_list = unit.location().all_locs
        for desired_coords in coord_list:
            elem = copy.deepcopy(unit_element)

            dx = desired_coords[0] - current_coords[0]
            dy = desired_coords[1] - current_coords[1]

            trans = get_transform(elem)
            if isinstance(trans, MatrixTransform):
                trans.x_c += dx
                trans.y_c += dy
            elif isinstance(trans, Translation):
                trans.x_c += dx
                trans.y_c += dy
            else:
                trans = Translation(None, (dx, dy))

            elem.set("transform", str(trans))

            elem.set("id", unit.province.name)
            elem.set("{http://www.inkscape.org/namespaces/inkscape}label", unit.province.name)

            group = self.cached_elements["unit_output"] if not use_moves_svg else self._moves_svg.getroot()
            group.append(elem)

    def highlight_retreating_units(self, svg):
        for unit in self.board.units:
            if unit == unit.province.dislodged_unit and unit.province in self.adjacent_provinces:
                self._draw_retreat_options(unit, svg)

    def _get_element_for_unit_type(self, unit_type) -> Element:
        # Just copy a random phantom unit
        if unit_type == UnitType.ARMY:
            layer: Element = self.cached_elements["army"]
        else:
            layer: Element = self.cached_elements["fleet"]
        return copy.deepcopy(layer.getchildren()[0])

    def _draw_retreat_options(self, unit: Unit, svg):
        root = svg.getroot()
        if not unit.retreat_options:
            self._draw_force_disband(unit.province.retreat_unit_coordinate, svg)
        # if we're drawing possible retreat locs, why show it as dislodged at all?
        # else:
        #     self._draw_disband(unit.location().retreat_unit_coordinate, svg)

        for retreat_province in unit.retreat_options:
            root.append(
                self._draw_retreat_move(
                    RetreatMove(retreat_province), unit.province.retreat_unit_coordinate, use_moves_svg=False
                )
            )

    def _initialize_scoreboard_locations(self) -> None:
        all_power_banners_element = get_svg_element(
            self.board_svg.getroot(), self.board.data["svg config"]["power_banners"]
        )
        self.scoreboard_power_locations: list[str] = []
        for power_element in all_power_banners_element:
            self.scoreboard_power_locations.append(power_element.get("transform"))

        # each power is placed in the right spot based on the transform field which has value of "tranlate($x,$y)" where x,y
        # are floating point numbers; we parse these via regex and sort by y-value
        self.scoreboard_power_locations.sort(
            key=lambda loc: float(re.match(r"translate\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)", loc).groups()[1])
        )

    def add_arrow_definition_to_svg(self, svg: ElementTree) -> None:
        defs: Element = svg.find("{http://www.w3.org/2000/svg}defs")
        if defs is None:
            defs = create_element("defs", {})
            svg.getroot().append(defs)
        # TODO: Check if 'arrow' id is already defined in defs
        arrow_marker: Element = self.create_element(
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
        arrow_path: Element = self.create_element(
            "path",
            {"d": "M 0,0 L 3,1.5 L 0,3 z"},
        )
        arrow_marker.append(arrow_path)
        defs.append(arrow_marker)
        red_arrow_marker: Element = self.create_element(
            "marker",
            {
                "id": "redarrow",
                "viewbox": "0 0 3 3",
                "refX": "1.5",
                "refY": "1.5",
                "markerWidth": "3",
                "markerHeight": "3",
                "orient": "auto-start-reverse",
            },
        )
        red_arrow_path: Element = self.create_element(
            "path",
            {"d": "M 0,0 L 3,1.5 L 0,3 z", "fill": "red"},
        )
        red_arrow_marker.append(red_arrow_path)
        defs.append(red_arrow_marker)

        ball_marker: Element = self.create_element(
            "marker",
            {
                "id": "ball",
                "viewbox": "0 0 3 3",
                # "refX": "1.5",
                # "refY": "1.5",
                "markerWidth": "3",
                "markerHeight": "3",
                "orient": "auto-start-reverse",
            },
        )
        ball_def: Element = self.create_element(
            "circle",
            {"r": "2", "fill": "black"},
        )
        ball_marker.append(ball_def)
        defs.append(ball_marker)

        data = self.board.data["players"].copy()
        data["None"] = {"color": "ffffff"}
        for mapping in itertools.product(data, data):
            gradient_def: Element = self.create_element("linearGradient", {"id": f"{mapping[0]}_{mapping[1]}"})
            first: Element = self.create_element(
                "stop", {"offset": "50%", "stop-color": f"#{data[mapping[0]]['color']}"}
            )
            second: Element = self.create_element(
                "stop", {"offset": "50%", "stop-color": f"#{data[mapping[1]]['color']}"}
            )
            gradient_def.append(first)
            gradient_def.append(second)
            defs.append(gradient_def)

    def color_element(self, element: Element, color: str, key="fill"):
        if len(color) == 6:  # Potentially buggy hack; just assume everything with length 6 is rgb without #
            color = f"#{color}"
        if element.get(key) is not None:
            element.set(key, color)
        if element.get("style") is not None and key in element.get("style"):
            style = element.get("style")
            style = re.sub(key + r":#[0-9a-fA-F]{6}", f"{key}:{color}", style)
            element.set("style", style)

    def create_element(self, tag: str, attributes: dict[str, any]) -> etree.Element:
        attributes_str = {key: str(val) for key, val in attributes.items()}
        return etree.Element(tag, attributes_str)

    # returns equivelent point within the map
    def normalize(self, point: tuple[float, float]):
        return (point[0] % self.board.data["svg config"]["map_width"], point[1])

    # returns closest point in a set
    # will wrap horizontally
    def get_closest_loc(self, possiblities: tuple[tuple[float, float]], coord: tuple[float, float]):
        possiblities = list(possiblities)
        crossed_pos = []
        crossed = []
        for p in possiblities:
            x = p[0]
            cx = coord[0]
            if abs(x - cx) > self.board.data["svg config"]["map_width"] / 2:
                crossed += [1]
                if x > cx:
                    x -= self.board.data["svg config"]["map_width"]
                else:
                    x += self.board.data["svg config"]["map_width"]
            else:
                crossed += [0]
            crossed_pos += [(x, p[1])]

        crossed = np.array(crossed)
        crossed_pos = np.array(crossed_pos)

        dists = crossed_pos - coord
        # penalty for crossing map is 500 px
        short_ind = np.argmin(np.linalg.norm(dists, axis=1) + 500 * crossed)
        return crossed_pos[short_ind].tolist()

    def loc_to_point(self, loc: Location, current: tuple[float, float], use_retreats=False):
        if not use_retreats:
            return self.get_closest_loc(loc.all_locs, current)
        else:
            return self.get_closest_loc(loc.all_rets, current)

    def pull_coordinate(
        self, anchor: tuple[float, float], coordinate: tuple[float, float], pull=None, limit=0.25
    ) -> tuple[float, float]:
        """
        Pull coordinate toward anchor by a small margin to give unit view breathing room. The pull will be limited to be
        no more than the given percent of the distance because otherwise small province size areas are hard to see.
        """

        if pull is None:
            pull = 1.5 * self.board.data["svg config"]["unit_radius"]

        ax, ay = anchor
        cx, cy = coordinate
        dx = ax - cx
        dy = ay - cy

        distance = math.sqrt(dx**2 + dy**2)
        if distance == 0:
            return coordinate

        # if the area is small, the pull can become too large of the percent of the total arrow length
        pull = min(pull, distance * limit)

        scale = pull / distance
        return cx + dx * scale, cy + dy * scale
