import numpy as np

from xml.etree.ElementTree import Element, ElementTree

from diplomacy.map_parser.vector.transform import TransGL3
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType
import logging

from shapely.geometry import Point
from typing import Callable
from diplomacy.persistence.province import Province

logger = logging.getLogger(__name__)

def get_svg_element(svg_root: ElementTree, element_id: str) -> Element:
    try:
        return svg_root.find(f'*[@id="{element_id}"]')
    except:
        logger.error(f"{element_id} isn't contained in svg_root")

def get_element_color(element: Element) -> str:
    style_string = element.get("style")
    if style_string is None:
        return None
    style = style_string.split(";")
    for value in style:
        prefix = "fill:#"
        if value.startswith(prefix):
            return value[len(prefix) :]


def get_player(element: Element, color_to_player: dict[str, Player]) -> Player:
    return color_to_player[get_element_color(element)]

def get_unit_coordinates(
    unit_data: Element,
) -> tuple[float, float]:
    path: Element = unit_data.find("{http://www.w3.org/2000/svg}path")

    x = path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx")
    y = path.get("{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy")
    if x == None or y == None:
        # find all the points the objects are at
        # take the center of the bounding box
        for path in unit_data.findall("{http://www.w3.org/2000/svg}path"):
            pathstr = path.get("d")
            coordinates = parse_path(pathstr, TransGL3(path))
            coordinates = np.array(sum(coordinates, start = []))
            minp = np.min(coordinates, axis=0)
            maxp = np.max(coordinates, axis=0)
            return ((minp + maxp) / 2).tolist()

    else:
        x = float(x)
        y = float(y)
        return TransGL3(path).transform((x, y))


def move_coordinate(
    former_coordinate: tuple[float, float],
    coordinate: tuple[float, float],
) -> tuple[float, float]:
    return (former_coordinate[0] + coordinate[0], former_coordinate[1] + coordinate[1])



# returns:
# new base_coordinate (= base_coordinate if not applicable),
# new former_coordinate (= former_coordinate if not applicable),
def _parse_path_command(
    command: str,
    args: list[tuple[float, float]],
    coordinate: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    reset = command.isupper()
    command = command.lower()

    if command in ["m", "c", "l", "t", "s", "q", "a"]:
        if reset:
            coordinate = (0, 0)
        return move_coordinate(coordinate, args[-1])  # Ignore all args except the last
    elif command in ["h", "v"]:
        coordinate = list(coordinate)
        if command == "h":
            index = 0
        else:
            index = 1
        if reset:
            coordinate[index] = 0
        coordinate[index] += args[0][0]
        return tuple(coordinate)
    else:
        raise RuntimeError(f"Unknown SVG path command: {command}")

def parse_path(path_string: str, translation: TransGL3):
    province_coordinates = [[]]
    command = None
    expected_arguments = 0
    current_index = 0
    path: list[str] = path_string.split()

    start = None
    coordinate = (0, 0)
    while current_index < len(path):
        if path[current_index][0].isalpha():
            if len(path[current_index]) != 1:
                # m20,70 is valid syntax, so move the 20,70 to the next element
                path.insert(current_index + 1, path[current_index][1:])
                path[current_index] = path[current_index][0]

            command = path[current_index]
            if command.lower() == "z":
                if start == None:
                    raise Exception("Invalid geometry: got 'z' on first element in a subgeometry")
                province_coordinates[-1].append(translation.transform(start))
                start = None
                current_index += 1
                if current_index < len(path):
                    # If we are closing, and there is more, there must be a second polygon (Chukchi Sea)
                    province_coordinates += [[]]
                    continue
                else:
                    break

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

        if command.lower() == "z":
            raise Exception("Invalid path, 'z' was followed by arguments")

        if len(path) < (current_index + expected_arguments):
            raise RuntimeError(f"Ran out of arguments for {command}")

        args = [
            (float(coord_string.split(",")[0]), float(coord_string.split(",")[-1]))
            for coord_string in path[current_index : current_index + expected_arguments]
        ]

        coordinate = _parse_path_command(
            command, args, coordinate
        )

        if start == None:
            start = coordinate

        province_coordinates[-1].append(translation.transform(coordinate))
        current_index += expected_arguments
    return province_coordinates

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

        # if not found:
        #     print("Not found!")

        for resident_data in remove:
            resident_dataset.remove(resident_data)
