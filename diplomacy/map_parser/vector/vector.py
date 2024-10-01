import re
from typing import Callable
from xml.etree.ElementTree import Element

import shapely
import itertools
import numpy as np
from lxml import etree
from scipy.spatial import cKDTree
from shapely.geometry import Point, Polygon

from diplomacy.map_parser.vector import cheat_parsing
from diplomacy.map_parser.vector.config_player import player_data, NEUTRAL, BLANK_CENTER
from diplomacy.map_parser.vector.config_svg import *
from diplomacy.map_parser.vector.transform import get_transform
from diplomacy.map_parser.vector.utils import (
    get_player,
    _get_unit_type,
    get_unit_coordinates,
    get_svg_element,
)
from diplomacy.persistence.board import Board
from diplomacy.persistence.phase import spring_moves
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, ProvinceType, Coast
from diplomacy.persistence.unit import Unit, UnitType

import copy

# TODO: (BETA) I made this file into a monster that is really ugly, let's clean it up!

# TODO: (BETA) all attribute getting should be in utils which we import and call utils.my_unit()
# TODO: (BETA) consistent in bracket formatting
NAMESPACE: dict[str, str] = {
    "inkscape": "{http://www.inkscape.org/namespaces/inkscape}",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "svg": "http://www.w3.org/2000/svg",
}


class Parser:
    def __init__(self):
        svg_root = etree.parse(SVG_PATH)

        self.land_layer: Element = get_svg_element(svg_root, LAND_PROVINCE_LAYER_ID)
        self.island_layer: Element = get_svg_element(svg_root, ISLAND_PROVINCE_LAYER_ID)
        self.island_fill_layer: Element = get_svg_element(svg_root, ISLAND_FILL_LAYER_ID)
        self.sea_layer: Element = get_svg_element(svg_root, SEA_PROVINCE_LAYER_ID)
        self.names_layer: Element = get_svg_element(svg_root, PROVINCE_NAMES_LAYER_ID)
        self.centers_layer: Element = get_svg_element(svg_root, SUPPLY_CENTER_LAYER_ID)
        self.units_layer: Element = get_svg_element(svg_root, UNITS_LAYER_ID)

        self.phantom_primary_armies_layer: Element = get_svg_element(svg_root, PHANTOM_PRIMARY_ARMY_LAYER_ID)
        self.phantom_retreat_armies_layer: Element = get_svg_element(svg_root, PHANTOM_RETREAT_ARMY_LAYER_ID)
        self.phantom_primary_fleets_layer: Element = get_svg_element(svg_root, PHANTOM_PRIMARY_FLEET_LAYER_ID)
        self.phantom_retreat_fleets_layer: Element = get_svg_element(svg_root, PHANTOM_RETREAT_FLEET_LAYER_ID)

        self.color_to_player: dict[str, Player | None] = {}
        self.name_to_province: dict[str, Province] = {}

        self.cache_provinces: set[Province] | None = None
        self.cache_adjacencies: set[tuple[str, str]] | None = None

    def parse(self) -> Board:
        players = set()
        for name, (color, vscc) in player_data.items():
            player = Player(name, color, vscc, set(), set())
            players.add(player)
            self.color_to_player[color] = player

        self.color_to_player[NEUTRAL] = None
        self.color_to_player[BLANK_CENTER] = None

        provinces = self._get_provinces()

        units = set()
        for province in provinces:
            unit = province.unit
            if unit:
                units.add(unit)

        return Board(players, provinces, units, spring_moves)

    def read_map(self) -> tuple[set[Province], set[tuple[str, str]]]:
        if self.cache_provinces is None:
            # TODO: (BETA) get names/centers/units without aid labeling and test equality against aid labeling
            # set coordinates and names
            self.cache_provinces: set[Province] = self._get_province_coordinates()
            if not PROVINCE_FILLS_LABELED:
                self._initialize_province_names(self.cache_provinces)

        provinces = copy.deepcopy(self.cache_provinces)
        for province in provinces:
            self.name_to_province[province.name] = province

        if self.cache_adjacencies is None:
            # set adjacencies
            # TODO: (BETA) province adjacency margin somtimes too high or too low, base it case by case on province size?
            self.cache_adjacencies = _get_adjacencies(provinces)
        adjacencies = copy.deepcopy(self.cache_adjacencies)

        return (provinces, adjacencies)

            

    def _get_provinces(self) -> set[Province]:
        provinces, adjacencies = self.read_map()
        for name1, name2 in adjacencies:
            province1 = self.name_to_province[name1]
            province2 = self.name_to_province[name2]
            province1.adjacent.add(province2)
            province2.adjacent.add(province1)

        # set coasts
        for province in provinces:
            province.set_coasts()
        cheat_parsing.set_coasts(self.name_to_province)
        cheat_parsing.set_canals(self.name_to_province)

        provinces = cheat_parsing.create_high_seas_and_sands(provinces, self.name_to_province)

        # really bad bandaid code, will fix later
        # some coasts aren't set because their only coasts are with cheat provinces which are set after coasts are
        for province in provinces:
            if province.type != ProvinceType.SEA and len(province.coasts) == 0:
                sea_provinces = set()
                for adjacent in province.adjacent:
                    if adjacent.type != ProvinceType.LAND:
                        sea_provinces.add(adjacent)
                if sea_provinces:
                    name = province.name + " coast"
                    province.coasts.add(Coast(name, None, None, sea_provinces, province))

        self._initialize_province_owners(self.land_layer)
        self._initialize_province_owners(self.island_fill_layer)

        # set supply centers
        if CENTER_PROVINCES_LABELED:
            self._initialize_supply_centers_assisted()
        else:
            self._initialize_supply_centers(provinces)

        # set units
        if UNIT_PROVINCES_LABELED:
            self._initialize_units_assisted()
        else:
            self._initialize_units(provinces)

        # set phantom unit coordinates for optimal unit placements
        self._set_phantom_unit_coordinates()

        # TODO: (BETA) yet another very bad bandaid, no time to fix it the right way
        cheat_parsing.fix_phantom_units(provinces)

        return provinces

    def _get_province_coordinates(self) -> set[Province]:
        # TODO: (BETA) don't hardcode translation
        land_provinces = self._create_provinces_type(self.land_layer, ProvinceType.LAND)
        island_provinces = self._create_provinces_type(self.island_layer, ProvinceType.ISLAND)
        sea_provinces = self._create_provinces_type(self.sea_layer, ProvinceType.SEA)
        return land_provinces.union(island_provinces).union(sea_provinces)

    # TODO: (BETA) can a library do all of this for us? more safety from needing to support wild SVG legal syntax
    def _create_provinces_type(
        self,
        provinces_layer: Element,
        province_type: ProvinceType,
    ) -> set[Province]:
        provinces = set()
        for province_data in provinces_layer.getchildren():
            path_string = province_data.get("d")
            if not path_string:
                raise RuntimeError("Province path data not found")
            path: list[str] = path_string.split()

            province_coordinates = []

            command = None
            expected_arguments = 0
            base_coordinate = (0, 0)
            former_coordinate = (0, 0)
            current_index = 0
            while current_index < len(path):
                if path[current_index][0].isalpha():
                    if len(path[current_index]) != 1:
                        # m20,70 is valid syntax, so move the 20,70 to the next element
                        path.insert(current_index + 1, path[current_index][1:])
                        path[current_index] = path[current_index][0]

                    command = path[current_index]
                    if command.lower() == "z":
                        expected_arguments = 0
                        former_coordinate = base_coordinate
                        province_coordinates.append(former_coordinate)
                        current_index += 1
                        continue
                    elif command.lower() in ["m", "l", "h", "v", "t"]:
                        expected_arguments = 1
                    elif command.lower() in ["s", "q"]:
                        expected_arguments = 2
                    elif command.lower() in ["c"]:
                        expected_arguments = 3
                    elif command.lower() in ["a"]:
                        expected_arguments = 4
                    else:
                        raise RuntimeError(f"Unknown SVG path command {command}")

                    current_index += 1

                if len(path) < (current_index + expected_arguments):
                    raise RuntimeError(f"Ran out of arguments for {command}")

                args = [
                    (float(coord_string.split(",")[0]), float(coord_string.split(",")[-1]))
                    for coord_string in path[current_index : current_index + expected_arguments]
                ]
                base_coordinate, former_coordinate = _parse_path_command(
                    command, args, base_coordinate, former_coordinate
                )
                province_coordinates.append(former_coordinate)
                current_index += expected_arguments

            layer_translation = get_transform(provinces_layer)
            this_translation = get_transform(province_data)
            for index, coordinate in enumerate(province_coordinates):
                province_coordinates[index] = this_translation.transform(layer_translation.transform(coordinate))

            name = None
            if PROVINCE_FILLS_LABELED:
                name = self._get_province_name(province_data)

            province = Province(
                name,
                province_coordinates,
                None,
                None,
                province_type,
                False,
                set(),
                set(),
                None,
                None,
                None,
            )

            provinces.add(province)
        return provinces

    def _initialize_province_owners(self, provinces_layer: Element) -> None:
        for province_data in provinces_layer.getchildren():
            name = self._get_province_name(province_data)
            self.name_to_province[name].owner = get_player(province_data, self.color_to_player)

    # Sets province names given the names layer
    def _initialize_province_names(self, provinces: set[Province]) -> None:
        def get_coordinates(name_data: Element) -> tuple[float, float]:
            return float(name_data.get("x")), float(name_data.get("y"))

        def set_province_name(province: Province, name_data: Element) -> None:
            if province.name is not None:
                raise RuntimeError(f"Province already has name: {province.name}")
            province.name = name_data.findall(".//svg:tspan", namespaces=NAMESPACE)[0].text

        initialize_province_resident_data(provinces, self.names_layer.getchildren(), get_coordinates, set_province_name)

    def _initialize_supply_centers_assisted(self) -> None:
        for center_data in self.centers_layer.getchildren():
            name = self._get_province_name(center_data)
            province = self.name_to_province[name]

            if province.has_supply_center:
                raise RuntimeError(f"{name} already has a supply center")
            province.has_supply_center = True

            owner = province.owner
            if owner:
                owner.centers.add(province)

            # TODO: (BETA): we cheat assume core = owner if exists because capital center symbols work different
            core = province.owner
            if not core:
                core_data = center_data.findall(".//svg:circle", namespaces=NAMESPACE)[1]
                core = get_player(core_data, self.color_to_player)
            province.core = core

    # Sets province supply center values
    def _initialize_supply_centers(self, provinces: set[Province]) -> None:

        def get_coordinates(supply_center_data: Element) -> tuple[float | None, float | None]:
            circles = supply_center_data.findall(".//svg:circle", namespaces=NAMESPACE)
            if not circles:
                return None, None
            circle = circles[0]
            base_coordinates = float(circle.get("cx")), float(circle.get("cy"))
            translation_coordinates = _get_translation_coordinates(supply_center_data)
            return (
                base_coordinates[0] + translation_coordinates[0],
                base_coordinates[1] + translation_coordinates[1],
            )

        def set_province_supply_center(province: Province, _: Element) -> None:
            if province.has_supply_center:
                raise RuntimeError(f"{province.name} already has a supply center")
            province.has_supply_center = True

        initialize_province_resident_data(provinces, self.centers_layer, get_coordinates, set_province_supply_center)

    def _set_province_unit(self, province: Province, unit_data: Element, coast: Coast) -> Unit:
        if province.unit:
            raise RuntimeError(f"{province.name} already has a unit")

        unit_type = _get_unit_type(unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0])
        color_data = unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0]
        player = get_player(color_data, self.color_to_player)
        # TODO: (BETA) tech debt: let's pass the coast in instead of only passing in coast when province has multiple
        if not coast and unit_type == UnitType.FLEET:
            coast = next((coast for coast in province.coasts), None)

        unit = Unit(unit_type, player, province, coast, None)
        province.unit = unit
        unit.player.units.add(unit)
        return unit

    def _initialize_units_assisted(self) -> None:
        for unit_data in self.units_layer.getchildren():
            province_name = self._get_province_name(unit_data)
            province, coast = self._get_province_and_coast(province_name)
            self._set_province_unit(province, unit_data, coast)

    # Sets province unit values
    def _initialize_units(self, provinces: set[Province]) -> None:
        def get_coordinates(unit_data: Element) -> tuple[float | None, float | None]:
            base_coordinates = unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0].get("d").split()[1].split(",")
            translation_coordinates = _get_translation_coordinates(unit_data)
            return (
                float(base_coordinates[0]) + translation_coordinates[0],
                float(base_coordinates[1]) + translation_coordinates[1],
            )

        initialize_province_resident_data(
            provinces, self.units_layer.getchildren(), get_coordinates, self._set_province_unit
        )

    def _set_phantom_unit_coordinates(self) -> None:
        army_layer_to_key = [
            (self.phantom_primary_armies_layer, "primary_unit_coordinate"),
            (self.phantom_retreat_armies_layer, "retreat_unit_coordinate"),
        ]
        for layer, province_key in army_layer_to_key:
            layer_translation = get_transform(layer)
            for unit_data in layer.getchildren():
                unit_translation = get_transform(unit_data)
                province = self._get_province(unit_data)
                coordinate = get_unit_coordinates(unit_data)
                setattr(province, province_key, unit_translation.transform(layer_translation.transform(coordinate)))

        fleet_layer_to_key = [
            (self.phantom_primary_fleets_layer, "primary_unit_coordinate"),
            (self.phantom_retreat_fleets_layer, "retreat_unit_coordinate"),
        ]
        for layer, province_key in fleet_layer_to_key:
            layer_translation = get_transform(layer)
            for unit_data in layer.getchildren():
                unit_translation = get_transform(unit_data)
                # This could either be a sea province or a land coast
                province_name = self._get_province_name(unit_data)

                # this is me writing bad code to get this out faster, will fix later when we clean up this file
                province, coast = self._get_province_and_coast(province_name)
                is_coastal = False
                for adjacent in province.adjacent:
                    if adjacent.type != ProvinceType.LAND:
                        is_coastal = True
                        break
                if not coast and province.type != ProvinceType.SEA and is_coastal:
                    # bad bandaid: this is probably an extra phantom unit, or maybe it's a primary one?
                    try:
                        coast = province.coast()
                    except Exception:
                        print("Warning: phantom unit skipped, if drawing some move doesn't work this might be why")
                        continue

                coordinate = get_unit_coordinates(unit_data)
                translated_coordinate = unit_translation.transform(layer_translation.transform(coordinate))
                if coast:
                    setattr(coast, province_key, translated_coordinate)
                else:
                    setattr(province, province_key, translated_coordinate)

    def _get_province_name(self, province_data: Element) -> str:
        return province_data.get(f"{NAMESPACE.get('inkscape')}label")

    def _get_province(self, province_data: Element) -> Province:
        return self.name_to_province[self._get_province_name(province_data)]

    def _get_province_and_coast(self, province_name: str) -> tuple[Province, Coast | None]:
        coast_suffix: str | None = None
        coast_names = {" (nc)", " (sc)", " (ec)", " (wc)"}

        for coast_name in coast_names:
            if province_name[len(province_name) - 5 :] == coast_name:
                province_name = province_name[: len(province_name) - 5]
                coast_suffix = coast_name[2:4]
                break

        province = self.name_to_province[province_name]
        coast = None
        if coast_suffix:
            coast = next((coast for coast in province.coasts if coast.name == f"{province_name} {coast_suffix}"), None)

        return province, coast


# returns:
# new base_coordinate (= base_coordinate if not applicable),
# new former_coordinate (= former_coordinate if not applicable),
def _parse_path_command(
    command: str,
    args: list[tuple[float, float]],
    base_coordinate: tuple[float, float],
    former_coordinate: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    if command.isupper():
        former_coordinate = (0, 0)
        command = command.lower()

    if command == "m":
        new_coordinate = move_coordinate(former_coordinate, args[0])
        return new_coordinate, new_coordinate
    elif command == "l" or command == "t" or command == "s" or command == "q" or command == "c" or command == "a":
        return base_coordinate, move_coordinate(former_coordinate, args[-1])  # Ignore all args except the last
    elif command == "h":
        return base_coordinate, move_coordinate(former_coordinate, args[0], ignore_y=True)
    elif command == "v":
        return base_coordinate, move_coordinate(former_coordinate, args[0], ignore_x=True)
    elif command == "z":
        raise RuntimeError("SVG command z should not be followed by any coordinates")
    else:
        raise RuntimeError(f"Unknown SVG path command: {command}")


def move_coordinate(
    former_coordinate: tuple[float, float],
    coordinate: tuple[float, float],
    ignore_x=False,
    ignore_y=False,
) -> tuple[float, float]:
    x = former_coordinate[0]
    y = former_coordinate[1]
    if not ignore_x:
        x += coordinate[0]
    if not ignore_y:
        y += coordinate[1]
    return x, y


# Returns the coordinates of the translation transform in the given element
def _get_translation_coordinates(element: Element) -> tuple[float, float]:
    transform = element.get("transform")
    if not transform:
        return None, None
    split = re.split(r"[(),]", transform)
    assert split[0] == "translate"
    return float(split[1]), float(split[2])


# Initializes relevant province data
# resident_dataset: SVG element whose children each live in some province
# get_coordinates: functions to get x and y child data coordinates in SVG
# function: method in Province that, given the province and a child element corresponding to that province, initializes
# that data in the Province
def initialize_province_resident_data(
    provinces: set[Province],
    resident_dataset: list[Element],
    get_coordinates: Callable[[Element], tuple[float, float]],
    resident_data_callback: Callable[[Province, Element], None],
) -> None:
    resident_dataset = set(resident_dataset)
    for province in provinces:
        remove = set()

        polygon = Polygon(province.coordinates)
        found = False
        for resident_data in resident_dataset:
            x, y = get_coordinates(resident_data)

            if not x or not y:
                remove.add(resident_data)
                continue

            point = Point((x, y))
            if polygon.contains(point):
                found = True
                resident_data_callback(province, resident_data)
                remove.add(resident_data)

        if not found:
            print("Not found!")

        for resident_data in remove:
            resident_dataset.remove(resident_data)


# Returns province adjacency set
def _get_adjacencies(provinces: set[Province]) -> set[tuple[str, str]]:
    adjacencies = set()
    for province1, province2 in itertools.permutations(provinces, 2):
        if shapely.distance(province1.geometry, province2.geometry) < PROVINCE_BORDER_MARGIN:
            adjacencies.add((province1.name, province2.name))
    
    def show_all():
        import matplotlib.pyplot as plt
        for p in provinces:
            plt.plot(*np.array(p.coordinates).T)
        plt.gca().invert_yaxis()
    breakpoint()
    return adjacencies

oneTrueParser = Parser()