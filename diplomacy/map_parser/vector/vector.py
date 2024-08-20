import re
from xml.etree.ElementTree import Element

import numpy as np
from lxml import etree
from scipy.spatial import cKDTree
from shapely.geometry import Point, Polygon

from diplomacy.map_parser.vector.config_svg import *
from diplomacy.map_parser.vector.utils import extract_value
from diplomacy.persistence.board import Board
from diplomacy.persistence.province import Province, ProvinceType
from diplomacy.persistence.unit import UnitType, Unit

# TODO: hold off on refactoring this because PR

# TODO: can a library do all of this for us?

# TODO: (MAP) cheat on x-wrap, high seas/sands, complicated coasts, canals
# TODO: (!) de-duplicate state in Unit/Province/Player knowledge of one another, have one source of truth
# TODO: (!) determine how edit base map state (province) should work (shared problem), allow all GMs? Only me? Only by admin in hub server?
# TODO: (DB) when updating DB map state, update SVG so it can be read if needed (everything we read here), and save SVG

NAMESPACE = {
    "inkscape": "{http://www.inkscape.org/namespaces/inkscape}",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "svg": "http://www.w3.org/2000/svg",
}


# Parse provinces, adjacencies, centers, and units
def parse() -> Board:
    land_data, island_data, sea_data, names_data, centers_data, units_data = get_svg_data()
    board = Board()
    # TODO: feed everything into the board state
    provinces = get_provinces(land_data, island_data, sea_data, names_data, centers_data, units_data)
    adjacencies = get_adjacencies(provinces)
    return board


# Gets provinces, names, centers, and units data from SVG
def get_svg_data() -> tuple[list[Element], list[Element], list[Element], list[Element], list[Element], list[Element]]:
    map_data = etree.parse(SVG_PATH)
    land_provinces_data = map_data.xpath(f'//*[@id="{LAND_PROVINCE_FILL_LAYER_ID}"]')[0].getchildren()
    island_provinces_data = map_data.xpath(f'//*[@id="{ISLAND_PROVINCE_BORDER_LAYER_ID}"]')[0].getchildren()
    sea_provinces_data = map_data.xpath(f'//*[@id="{SEA_PROVINCE_BORDER_LAYER_ID}"]')[0].getchildren()
    names_data = map_data.xpath(f'//*[@id="{PROVINCE_NAMES_LAYER_ID}"]')[0].getchildren()
    centers_data = map_data.xpath(f'//*[@id="{SUPPLY_CENTER_LAYER_ID}"]')[0].getchildren()
    units_data = map_data.xpath(f'//*[@id="{UNITS_LAYER_ID}"]')[0].getchildren()
    return (
        land_provinces_data,
        island_provinces_data,
        sea_provinces_data,
        names_data,
        centers_data,
        units_data,
    )


# Creates and initializes provinces
def get_provinces(
    land_provinces_data: list[Element],
    island_provinces_data: list[Element],
    sea_provinces_data: list[Element],
    names_data: list[Element],
    centers_data: list[Element],
    units_data: list[Element],
) -> set[Province]:
    provinces_data = land_provinces_data + island_provinces_data
    provinces = create_provinces(provinces_data, sea_provinces_data)

    if not PROVINCE_FILLS_LABELED:
        initialize_province_names(provinces, names_data)

    name_to_province = {}
    for province in provinces:
        name_to_province[province.name] = province

    if CENTER_PROVINCES_LABELED:
        initialize_supply_centers_assisted(name_to_province, centers_data)
    else:
        initialize_supply_centers(provinces, centers_data)

    if UNIT_PROVINCES_LABELED:
        initialize_units_assisted(name_to_province, units_data)
    else:
        initialize_units(provinces, units_data)

    return provinces


# Creates provinces with border coordinates
def create_provinces(
    land_provinces_data: list[Element],
    sea_provinces_data: list[Element],
) -> set[Province]:
    # TODO: might be island
    land_provinces = create_provinces_type(land_provinces_data, ProvinceType.LAND)
    sea_provinces = create_provinces_type(sea_provinces_data, ProvinceType.SEA)
    return land_provinces.union(sea_provinces)


def create_provinces_type(
    provinces_data: list[Element],
    province_type: ProvinceType,
) -> set[Province]:
    provinces = set()
    for province_data in provinces_data:
        path = province_data.get("d")
        if not path:
            continue
        path = path.split()

        province_coordinates = []

        command = None
        base_coordinate = [0, 0]
        former_coordinate = (0, 0)
        for element in path:
            split = element.split(",")
            if len(split) == 1:
                command = split[0]
                if command == "z":
                    former_coordinate = base_coordinate
                    province_coordinates.append(former_coordinate)
            elif len(split) == 2:
                coordinate = (float(split[0]), float(split[1]))
                former_coordinate, base_coordinate = parse_path_command(
                    command, coordinate, base_coordinate, former_coordinate
                )
                province_coordinates.append(former_coordinate)
            else:
                print("Unknown SVG path coordinate:", split)
                continue

        province = Province(province_coordinates, province_type)

        if PROVINCE_FILLS_LABELED:
            name = province_data.get(f"{NAMESPACE.get('inkscape')}label")
            province.set_name(name)

        provinces.add(province)
    return provinces


# returns:
# new coordinate (= former_coordinate if not applicable),
# new base_coordinate (= base_coordinate if not applicable),
def parse_path_command(
    command: str,
    coordinate: Tuple[float, float],
    base_coordinate: Tuple[float, float],
    former_coordinate: Tuple[float, float],
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    if command.isupper():
        # TODO: (!) uppercase C has a massive province movement
        former_coordinate = (0, 0)
        command = command.lower()

    if command == "m":
        new_coordinate = get_coordinate(coordinate, former_coordinate, True, True)
        return new_coordinate, new_coordinate
    elif command == "l" or command == "c" or command == "s" or command == "q" or command == "t" or command == "a":
        return get_coordinate(coordinate, former_coordinate, True, True), base_coordinate
    elif command == "h":
        return get_coordinate(coordinate, former_coordinate, True, False), base_coordinate
    elif command == "v":
        return get_coordinate(coordinate, former_coordinate, False, True), base_coordinate
    elif command == "z":
        print("SVG command z should not be followed by any coordinates")
        return former_coordinate, base_coordinate
    else:
        print("Unknown SVG path command:", command)
        return former_coordinate, base_coordinate


def get_coordinate(
    coordinate: Tuple[float, float],
    former_coordinate: Tuple[float, float],
    use_x: bool,
    use_y: bool,
) -> Tuple[float, float]:
    x = former_coordinate[0]
    y = former_coordinate[1]
    if use_x:
        x += coordinate[0]
    if use_y:
        y += coordinate[1]
    return x, y


# Sets province names given the names layer
def initialize_province_names(provinces: Set[Province], names_data: List[Element]) -> NoReturn:
    def get_coordinates(name_data: Element) -> Tuple[float, float]:
        return float(name_data.get("x")), float(name_data.get("y"))

    def set_province_name(province: Province, name_data: Element) -> NoReturn:
        if province.name is not None:
            print(province.name, "already has a name!")
        province.set_name(name_data.findall(".//svg:tspan", namespaces=NAMESPACE)[0].text)

    initialize_province_resident_data(provinces, names_data, get_coordinates, set_province_name)


def initialize_supply_centers_assisted(provinces: Mapping[str, Province], centers_data: List[Element]) -> NoReturn:
    for center_data in centers_data:
        province_name = center_data.get(f"{NAMESPACE.get('inkscape')}label")
        province = provinces.get(province_name)
        if not province:
            print("Province not found for center in: ", province_name)
        else:
            if province.has_supply_center:
                print("Province: ", province_name, "already has a supply center!")
            province.set_has_supply_center(True)


# Sets province supply center values
def initialize_supply_centers(provinces: Set[Province], centers_data: List[Element]) -> NoReturn:

    def get_coordinates(supply_center_data: Element) -> Tuple[Optional[float], Optional[float]]:
        circles = supply_center_data.findall(".//svg:circle", namespaces=NAMESPACE)
        if not circles:
            return None, None
        circle = circles[0]
        base_coordinates = float(circle.get("cx")), float(circle.get("cy"))
        translation_coordinates = get_translation_coordinates(supply_center_data)
        return (
            base_coordinates[0] + translation_coordinates[0],
            base_coordinates[1] + translation_coordinates[1],
        )

    def set_province_supply_center(province: Province, _: Element) -> NoReturn:
        if province.has_supply_center:
            print(province.name, "already has a supply center!")
        province.set_has_supply_center(True)

    initialize_province_resident_data(provinces, centers_data, get_coordinates, set_province_supply_center)


def set_province_unit(province: Province, unit_data: Element, board: Board) -> NoReturn:
    if province.unit:
        print("Province", province.name, "already has a unit!")

    player = extract_value(
        unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0].get("style"),
        "fill",
    )

    num_sides = unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0].get(
        "{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}sides"
    )
    if num_sides == "3":
        unit = Unit(UnitType.ARMY, player, province)
    elif num_sides == "6":
        unit = Unit(UnitType.FLEET, player, province)
    else:
        raise RuntimeError(f"Unit has {num_sides} sides which does not match any unit definition.")

    province.unit = unit


def initialize_units_assisted(provinces: Mapping[str, Province], units_data: List[Element]) -> NoReturn:
    for unit_data in units_data:
        province_name = unit_data.get(f"{NAMESPACE.get('inkscape')}label")
        province = provinces.get(province_name)
        if not province:
            print("Province not found for unit in: ", province_name)
        else:
            set_province_unit(province, unit_data)


# Sets province unit values
def initialize_units(provinces: Set[Province], units_data: List[Element]) -> NoReturn:
    def get_coordinates(unit_data: Element) -> Tuple[Optional[float], Optional[float]]:
        base_coordinates = unit_data.findall(".//svg:path", namespaces=NAMESPACE)[0].get("d").split()[1].split(",")
        translation_coordinates = get_translation_coordinates(unit_data)
        return (
            float(base_coordinates[0]) + translation_coordinates[0],
            float(base_coordinates[1]) + translation_coordinates[1],
        )

    initialize_province_resident_data(provinces, units_data, get_coordinates, set_province_unit)


# Returns the coordinates of the translation transform in the given element
def get_translation_coordinates(
    element: Element,
) -> Tuple[Optional[float], Optional[float]]:
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
    provinces: Set[Province],
    resident_dataset: List[Element],
    get_coordinates: Callable[[Element], Tuple[Optional[float], Optional[float]]],
    function: Callable[[Province, Element], NoReturn],
) -> NoReturn:
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
                function(province, resident_data)
                remove.add(resident_data)

        if not found:
            print("Not found!")

        for resident_data in remove:
            resident_dataset.remove(resident_data)


# Returns province adjacency set
def get_adjacencies(provinces: Set[Province]) -> Set[Tuple[str, str]]:
    # TODO: (MAP) fix adjacencies, currently points are obtained inaccurately: can compare x/y extremes on provinces with SVG
    # cKDTree is great, but it doesn't intelligently exclude clearly impossible cases of which we will have many
    coordinates = {}
    for province in provinces:
        x_sort = sorted(province.coordinates, key=lambda coordinate: coordinate[0])
        y_sort = sorted(province.coordinates, key=lambda coordinate: coordinate[1])
        coordinates[province.name] = {"x_sort": x_sort, "y_sort": y_sort}

    adjacencies = set()
    for province_1, coordinates_1 in coordinates.items():
        tree_1 = cKDTree(np.array(coordinates_1["x_sort"]))

        x1_min = coordinates_1["x_sort"][0][0]
        x1_max = coordinates_1["x_sort"][-1][0]
        y1_min = coordinates_1["y_sort"][0][1]
        y1_max = coordinates_1["y_sort"][-1][1]

        for province_2, coordinates_2 in coordinates.items():
            if province_1 >= province_2:
                # check each pair once, don't check self-self
                continue

            x2_min = coordinates_2["x_sort"][0][0]
            x2_max = coordinates_2["x_sort"][-1][0]
            y2_min = coordinates_2["y_sort"][0][1]
            y2_max = coordinates_2["y_sort"][-1][1]

            if x1_min > x2_max or x1_max < x2_min:
                # out of x-scope
                continue

            if y1_min > y2_max or y1_max < y2_min:
                # out of y-scope
                continue

            for point in coordinates_2["x_sort"]:
                if tree_1.query_ball_point(point, r=PROVINCE_BORDER_MARGIN):
                    adjacencies.add((province_1, province_2))
                    continue
    return adjacencies
