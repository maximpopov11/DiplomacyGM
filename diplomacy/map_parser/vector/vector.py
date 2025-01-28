import copy
import itertools
import json
import logging
import time
from typing import Callable
from xml.etree.ElementTree import Element

import shapely
from lxml import etree
from shapely.geometry import Point

from diplomacy.map_parser.vector.transform import get_transform
from diplomacy.map_parser.vector.utils import get_player, get_unit_coordinates, get_svg_element, parse_path
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province, ProvinceType, Coast
from diplomacy.persistence.unit import Unit, UnitType

# TODO: (BETA) all attribute getting should be in utils which we import and call utils.my_unit()
# TODO: (BETA) consistent in bracket formatting
NAMESPACE: dict[str, str] = {
    "inkscape": "{http://www.inkscape.org/namespaces/inkscape}",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "svg": "http://www.w3.org/2000/svg",
}

logger = logging.getLogger(__name__)


class Parser:
    def __init__(self, data: str):
        self.datafile = data

        with open(f"config/{data}", "r") as f:
            self.data = json.load(f)

        svg_root = etree.parse(self.data["file"])

        self.layers = self.data["svg config"]

        self.land_layer: Element = get_svg_element(svg_root, self.layers["land_layer"])
        self.island_layer: Element = get_svg_element(svg_root, self.layers["island_borders"])
        self.island_fill_layer: Element = get_svg_element(svg_root, self.layers["island_fill_layer"])
        self.sea_layer: Element = get_svg_element(svg_root, self.layers["sea_borders"])
        self.names_layer: Element = get_svg_element(svg_root, self.layers["province_names"])
        self.centers_layer: Element = get_svg_element(svg_root, self.layers["supply_center_icons"])
        if self.layers["detect_starting_units"]:
            self.units_layer: Element = get_svg_element(svg_root, self.layers["starting_units"])
        else:
            self.units_layer = None
        self.power_banner_layer: Element = get_svg_element(svg_root, self.layers["power_banners"])

        self.phantom_primary_armies_layer: Element = get_svg_element(svg_root, self.layers["army"])
        self.phantom_retreat_armies_layer: Element = get_svg_element(svg_root, self.layers["retreat_army"])
        self.phantom_primary_fleets_layer: Element = get_svg_element(svg_root, self.layers["fleet"])
        self.phantom_retreat_fleets_layer: Element = get_svg_element(svg_root, self.layers["retreat_fleet"])

        self.color_to_player: dict[str, Player | None] = {}
        self.name_to_province: dict[str, Province] = {}

        self.cache_provinces: set[Province] | None = None
        self.cache_adjacencies: set[tuple[str, str]] | None = None

    def parse(self) -> Board:
        logger.debug("map_parser.vector.parse.start")
        start = time.time()

        players = set()
        for name, data in self.data["players"].items():
            color = data["color"]
            vscc = data["vscc"]
            iscc = data["iscc"]
            player = Player(name, color, vscc, iscc, set(), set())
            players.add(player)
            self.color_to_player[color] = player

        self.color_to_player[self.data["svg config"]["neutral"]] = None
        self.color_to_player[self.data["svg config"]["neutral_sc"]] = None

        provinces = self._get_provinces()

        units = set()
        for province in provinces:
            unit = province.unit
            if unit:
                units.add(unit)

        elapsed = time.time() - start
        logger.info(f"map_parser.vector.parse: {elapsed}s")

        return Board(players, provinces, units, phase.initial(), self.data, self.datafile)

    def read_map(self) -> tuple[set[Province], set[tuple[str, str]]]:
        if self.cache_provinces is None:
            # set coordinates and names
            raw_provinces: set[Province] = self._get_province_coordinates()
            cache = []
            self.cache_provinces = set()
            for province in raw_provinces:
                if province.name in cache:
                    logger.warning(f"{province.name} repeats in map, ignoring...")
                    continue
                cache.append(province.name)
                self.cache_provinces.add(province)

            if not self.layers["province_labels"]:
                self._initialize_province_names(self.cache_provinces)

        provinces = copy.deepcopy(self.cache_provinces)
        for province in provinces:
            self.name_to_province[province.name] = province

        if self.cache_adjacencies is None:
            # set adjacencies
            self.cache_adjacencies = self._get_adjacencies(provinces)
        adjacencies = copy.deepcopy(self.cache_adjacencies)

        return (provinces, adjacencies)

    def names_to_provinces(self, names: set[str]):
        return map((lambda n: self.name_to_province[n]), names)

    def add_province_to_board(self, provinces: set[Province], province: Province) -> set[Province]:
        provinces = {x for x in provinces if x.name != province.name}
        provinces.add(province)
        self.name_to_province[province.name] = province
        return provinces

    def json_cheats(self, provinces: set[Province]) -> set[Province]:
        if not "overrides" in self.data:
            return
        if "high provinces" in self.data["overrides"]:
            for name, data in self.data["overrides"]["high provinces"].items():
                for index in range(1, data["num"] + 1):
                    province = Province(
                        name + str(index),
                        [],
                        None,
                        None,
                        getattr(ProvinceType, data["type"]),
                        False,
                        set(),
                        set(),
                        None,
                        None,
                        None,
                    )
                    provinces = self.add_province_to_board(provinces, province)
            for name, data in self.data["overrides"]["high provinces"].items():
                adjacent = tuple(self.names_to_provinces(data["adjacencies"]))
                for index in range(1, data["num"] + 1):
                    high_province = self.name_to_province[name + str(index)]
                    high_province.adjacent.update(adjacent)
                    for ad in adjacent:
                        ad.adjacent.add(high_province)

        if "provinces" in self.data["overrides"]:
            for name, data in self.data["overrides"]["provinces"].items():
                province = self.name_to_province[name]
                # TODO: Some way to specifiy whether or not to clear other adjacencies?
                if "adjacencies" in data:
                    province.adjacent.update(self.names_to_provinces(data["adjacencies"]))
                if "remove_adjacencies" in data:
                    province.adjacent.difference_update(self.names_to_provinces(data["remove_adjacencies"]))
                if "coasts" in data:
                    province.coasts = set()
                    for coast_name, coast_adjacent in data["coasts"].items():
                        coast = Coast(f"{name} {coast_name}", None, None, set(self.names_to_provinces(coast_adjacent)), province)
                        province.coasts.add(coast)
                if "unit_loc" in data:
                    for coordinate in data["unit_loc"]:
                        province.primary_unit_coordinate = tuple(coordinate)
                    province.all_locs.add(tuple(coordinate))
                if "retreat_unit_loc" in data:
                    for coordinate in data["retreat_unit_loc"]:
                        province.retreat_unit_coordinate = tuple(coordinate)
                    province.all_rets.add(tuple(coordinate))

        return provinces

    def _get_provinces(self) -> set[Province]:
        provinces, adjacencies = self.read_map()
        for name1, name2 in adjacencies:
            province1 = self.name_to_province[name1]
            province2 = self.name_to_province[name2]
            province1.adjacent.add(province2)
            province2.adjacent.add(province1)

        provinces = self.json_cheats(provinces)

        # set coasts
        for province in provinces:
            province.set_coasts()

        self._initialize_province_owners(self.land_layer)
        self._initialize_province_owners(self.island_fill_layer)

        # set supply centers
        # if self.data["svg config"]["coring"]:
        if self.layers["center_labels"]:
            self._initialize_supply_centers_assisted()
        else:
            self._initialize_supply_centers(provinces)

        # set units
        if self.units_layer is not None:
            if self.layers["unit_labels"]:
                self._initialize_units_assisted()
            else:
                self._initialize_units(provinces)

        # set phantom unit coordinates for optimal unit placements
        self._set_phantom_unit_coordinates()

        for province in provinces:
            province.all_locs.add(province.primary_unit_coordinate)
            province.all_rets.add(province.retreat_unit_coordinate)
            for coast in province.coasts:
                coast.all_locs.add(coast.primary_unit_coordinate)
                coast.all_rets.add(coast.retreat_unit_coordinate)

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
        prev_names = set()
        for province_data in provinces_layer.getchildren():
            path_string = province_data.get("d")
            if not path_string:
                raise RuntimeError("Province path data not found")
            layer_translation = get_transform(provinces_layer)
            this_translation = get_transform(province_data)

            province_coordinates = parse_path(path_string, layer_translation, this_translation)

            if len(province_coordinates) <= 1:
                poly = shapely.Polygon(province_coordinates[0])
            else:
                poly = shapely.MultiPolygon(map(shapely.Polygon, province_coordinates))
                poly = poly.buffer(0.1)
                import matplotlib.pyplot as plt

                if not poly.is_valid:
                    print(f"MULTIPOLYGON IS NOT VALID (name: {self._get_province_name(province_data)})")
                    for subpoly in poly.geoms:
                        plt.plot(*subpoly.exterior.xy)
                    plt.show()

            province_coordinates = shapely.MultiPolygon()

            name = None
            if self.layers["province_labels"]:
                name = self._get_province_name(province_data)

            province = Province(
                name,
                poly,
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
            # if not core:
            #     core_data = center_data.findall(".//svg:circle", namespaces=NAMESPACE)[1]
            #     core = get_player(core_data, self.color_to_player)
            province.core = core

    # Sets province supply center values
    def _initialize_supply_centers(self, provinces: set[Province]) -> None:

        def get_coordinates(supply_center_data: Element) -> tuple[float | None, float | None]:
            circles = supply_center_data.findall(".//svg:circle", namespaces=NAMESPACE)
            if not circles:
                return None, None
            circle = circles[0]
            base_coordinates = float(circle.get("cx")), float(circle.get("cy"))
            trans = get_transform(supply_center_data)
            return trans.transform(base_coordinates)

        def set_province_supply_center(province: Province, _: Element) -> None:
            if province.has_supply_center:
                raise RuntimeError(f"{province.name} already has a supply center")
            province.has_supply_center = True

        initialize_province_resident_data(provinces, self.centers_layer, get_coordinates, set_province_supply_center)

    def _set_province_unit(self, province: Province, unit_data: Element, coast: Coast = None) -> Unit:
        if province.unit:
            return
            raise RuntimeError(f"{province.name} already has a unit")

        unit_type = self._get_unit_type(unit_data)

        # assume that all starting units are on provinces colored in to their color
        player = province.owner
        if province.owner == None:
            raise Exception(f"{province.name} has a unit, but isn't owned by any country")

        # color_data = unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0]
        # player = get_player(color_data, self.color_to_player)
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
            if self.data["svg config"]["unit_type_labeled"]:
                province_name = province_name[1:]
            province, coast = self._get_province_and_coast(province_name)
            self._set_province_unit(province, unit_data, coast)

    # Sets province unit values
    def _initialize_units(self, provinces: set[Province]) -> None:
        def get_coordinates(unit_data: Element) -> tuple[float | None, float | None]:
            base_coordinates = tuple(
                map(float, unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0].get("d").split()[1].split(","))
            )
            trans = get_transform(unit_data)
            return trans.transform(base_coordinates)

        initialize_province_resident_data(provinces, self.units_layer, get_coordinates, self._set_province_unit)

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
                setattr(province, province_key, layer_translation.transform(unit_translation.transform(coordinate)))

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
                        print(
                            f"Warning: phantom unit skipped, if drawing some move doesn't work this might be why: {province_name} {province_key}"
                        )
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

    # Returns province adjacency set
    def _get_adjacencies(self, provinces: set[Province]) -> set[tuple[str, str]]:
        adjacencies = set()

        # Combinations so that we only have (A, B) and not (B, A) or (A, A)
        for province1, province2 in itertools.combinations(provinces, 2):
            if shapely.distance(province1.geometry, province2.geometry) < self.layers["border_margin_hint"]:
                adjacencies.add((province1.name, province2.name))
        # import matplotlib.pyplot as plt
        # for p in provinces:
        #     if isinstance(p.geometry, shapely.Polygon):
        #         plt.plot(*p.geometry.exterior.xy)
        #     else:
        #         for geo in p.geometry.geoms:
        #             plt.plot(*geo.exterior.xy)
        # plt.gca().invert_yaxis()
        # plt.show()
        return adjacencies

    def _get_unit_type(self, unit_data: Element) -> UnitType:
        if self.data["svg config"]["unit_type_labeled"]:
            name = self._get_province_name(unit_data)
            if name is None:
                raise RuntimeError("Unit has no name, but unit_type_labeled = true")
            if name.lower().startswith("f"):
                return UnitType.FLEET
            if name.lower().startswith("a"):
                return UnitType.ARMY
            else:
                raise RuntimeError(f"Unit types are labeled, but {name} doesn't start with F or A")
        unit_data = unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0]
        num_sides = unit_data.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}sides")
        if num_sides == "3":
            return UnitType.FLEET
        elif num_sides == "6":
            return UnitType.ARMY
        else:
            return UnitType.ARMY
            raise RuntimeError(f"Unit has {num_sides} sides which does not match any unit definition.")


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

        found = False
        for resident_data in resident_dataset:
            x, y = get_coordinates(resident_data)

            if not x or not y:
                remove.add(resident_data)
                continue

            point = Point((x, y))
            if province.geometry.contains(point):
                found = True
                resident_data_callback(province, resident_data)
                remove.add(resident_data)

        if not found:
            print("Not found!")

        for resident_data in remove:
            resident_dataset.remove(resident_data)


parsers = {}


def get_parser(name: str) -> Parser:
    if name in parsers:
        return parsers[name]
    else:
        parsers[name] = Parser(name)
        return parsers[name]


# oneTrueParser = Parser()
