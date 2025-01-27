import numpy as np

from xml.etree.ElementTree import Element, ElementTree

from diplomacy.map_parser.vector.transform import Transform, EmptyTransform, get_transform
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType


def get_svg_element(svg_root: ElementTree, element_id: str) -> Element:
    try:
        return svg_root.xpath(f'//*[@id="{element_id}"]')[0]
    except:
        print(element_id)

def get_element_color(element: Element) -> str:
    style = element.get("style").split(";")
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
            coordinates = parse_path(pathstr, EmptyTransform(None), get_transform(path))
            coordinates = np.array(sum(coordinates, start = []))
            minp = np.min(coordinates, axis=0)
            maxp = np.max(coordinates, axis=0)
            return ((minp + maxp) / 2).tolist()

    else:
        x = float(x)
        y = float(y)
        return get_transform(path).transform((x, y))

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


def parse_path(path_string: str, layer_translation: Transform, this_translation: Transform):
    province_coordinates = [[]]
    command = None
    expected_arguments = 0
    base_coordinate = (0, 0)
    former_coordinate = (0, 0)
    current_index = 0
    path: list[str] = path_string.split()


    while current_index < len(path):
        if path[current_index][0].isalpha():
            if len(path[current_index]) != 1:
                # m20,70 is valid syntax, so move the 20,70 to the next element
                path.insert(current_index + 1, path[current_index][1:])
                path[current_index] = path[current_index][0]

            command = path[current_index]
            if command.lower() == "z":
                expected_arguments = 0
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
        if expected_arguments != 0:
            if len(path) < (current_index + expected_arguments):
                raise RuntimeError(f"Ran out of arguments for {command}")

            args = [
                (float(coord_string.split(",")[0]), float(coord_string.split(",")[-1]))
                for coord_string in path[current_index : current_index + expected_arguments]
            ]
            base_coordinate, former_coordinate = _parse_path_command(
                command, args, base_coordinate, former_coordinate
            )
        else:
            former_coordinate = base_coordinate

        province_coordinates[-1].append(layer_translation.transform(this_translation.transform(former_coordinate)))
        current_index += expected_arguments
        if current_index < len(path) and command.lower() == "z":
            # If we are closing, and there is more, there must be a second polygon (Chukchi Sea)
            province_coordinates += [[]]
    return province_coordinates