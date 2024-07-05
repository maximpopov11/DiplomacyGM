import re

from lxml import etree
from shapely.geometry import Point, Polygon

from vector.config import *
from vector.province import Province
from vector.utils import extract_value

NAMESPACE = {
    'inkscape': '{http://www.inkscape.org/namespaces/inkscape}',
    'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
    'svg': 'http://www.w3.org/2000/svg',
}


# Parse provinces, adjacencies, centers, and units
def parse_map_data():
    provinces_data, names_data, centers_data, units_data = get_svg_data()
    provinces = get_provinces(provinces_data, names_data, centers_data, units_data)
    adjacencies = get_adjacencies(provinces)

    centers = []
    units = []
    for province in provinces:
        if province.has_supply_center:
            centers.append(province.name)
        if province.unit:
            units.append(province.name)

    print(centers)
    print(units)


# Gets provinces, names, centers, and units data from SVG
def get_svg_data():
    map_data = etree.parse(SVG_PATH)
    provinces_data = map_data.xpath(f'//*[@id="{LAND_PROVINCE_FILL_LAYER_ID}"]')[0].getchildren()
    names_data = map_data.xpath(f'//*[@id="{PROVINCE_NAMES_LAYER_ID}"]')[0].getchildren()
    centers_data = map_data.xpath(f'//*[@id="{SUPPLY_CENTER_LAYER_ID}"]')[0].getchildren()
    units_data = map_data.xpath(f'//*[@id="{UNITS_LAYER_ID}"]')[0].getchildren()
    return provinces_data, names_data, centers_data, units_data


# Creates and initializes provinces
def get_provinces(provinces_data, names_data, centers_data, units_data):
    provinces = create_provinces(provinces_data, PROVINCE_FILLS_LABELED)

    if not PROVINCE_FILLS_LABELED:
        initialize_province_names(provinces, names_data)

    initialize_supply_centers(provinces, centers_data)
    initialize_units(provinces, units_data)
    return provinces


# Creates provinces with border coordinates
def create_provinces(provinces_data, province_fills_labeled):
    provinces = []
    for province_data in provinces_data:
        path = province_data.get('d')
        if not path:
            continue
        path = path.split()

        province_coordinates = []
        last_coordinate = None
        for element in path:
            split = element.split(',')

            # Only accept data formatted x,y to ignore irrelevant SVG data
            if len(split) != 2:
                continue

            if not last_coordinate:
                coordinate = (float(split[0]), float(split[1]))
            else:
                # Coordinate data in an SVG is provided relative to last coordinate after the first
                coordinate = (last_coordinate[0] + float(split[0]), last_coordinate[1] + float(split[1]))
            last_coordinate = coordinate
            province_coordinates.append(coordinate)

        province = Province(province_coordinates)

        if province_fills_labeled:
            name = province_data.get(f"{NAMESPACE.get('inkscape')}label")
            province.set_name(name)

        provinces.append(province)

    return provinces


# Sets province names given the names layer
def initialize_province_names(provinces, names_data):
    def get_coordinates(name_data):
        return name_data.get('x'), name_data.get('y')

    def set_province_name(province, name_data):
        if province.name is not None:
            print(province.name, 'already has a name!')
        province.set_name(name_data.findall('.//svg:tspan', namespaces=NAMESPACE)[0].text)

    initialize_province_resident_data(provinces, names_data, get_coordinates, set_province_name)


# Sets province supply center values
def initialize_supply_centers(provinces, centers_data):
    def get_coordinates(supply_center_data):
        circles = supply_center_data.findall('.//svg:circle', namespaces=NAMESPACE)
        if not circles:
            return None, None
        circle = circles[0]
        base_coordinates = float(circle.get('cx')), float(circle.get('cy'))
        translation_coordinates = get_translation_coordinates(supply_center_data)
        return base_coordinates[0] + translation_coordinates[0], base_coordinates[1] + translation_coordinates[1]

    def set_province_supply_center(province, _):
        if province.has_supply_center:
            print(province.name, 'already has a supply center!')
        province.set_has_supply_center(True)

    initialize_province_resident_data(provinces, centers_data, get_coordinates, set_province_supply_center)


# Sets province unit values
def initialize_units(provinces, units_data):
    def get_coordinates(unit_data):
        base_coordinates = unit_data.findall('.//svg:path', namespaces=NAMESPACE)[0].get('d').split()[1].split(',')
        translation_coordinates = get_translation_coordinates(unit_data)
        return float(base_coordinates[0]) + translation_coordinates[0], float(base_coordinates[1]) + translation_coordinates[1]

    def set_province_unit(province, unit_data):
        if province.unit is not None:
            print(province.name, 'already has a unit!')
        # TODO: The unit type is derived from shape which lives in sodipodi:type
        #  for which we might need to add sodipop to the namespace? Yay we did it now so when we get to this it'll be easier
        unit_type = 'Lets pretend this is a unit type'
        player = extract_value(unit_data.findall('.//svg:path', namespaces=NAMESPACE)[0].get('style'), 'fill')
        province.set_unit({'type': unit_type, 'player': player})

    initialize_province_resident_data(provinces, units_data, get_coordinates, set_province_unit)


# Returns the coordinates of the translation transform in the given element
def get_translation_coordinates(element):
    transform = element.get('transform')
    if not transform:
        return None, None
    split = re.split(r'[(),]', transform)
    assert split[0] == 'translate'
    return float(split[1]), float(split[2])


# Initializes relevant province data
# resident_dataset: SVG element whose children each live in some province
# get_coordinates: functions to get x and y child data coordinates in SVG
# function: method in Province that, given the province and a child element corresponding to that province, initializes
# that data in the Province
def initialize_province_resident_data(provinces, resident_dataset, get_coordinates, function):
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
            print('Not found!')

        for resident_data in remove:
            resident_dataset.remove(resident_data)


# Returns province adjacency set
def get_adjacencies(provinces):
    coordinates = []
    for province in provinces:
        for coordinate in province.coordinates:
            coordinates.append({'x': coordinate[0], 'y': coordinate[1], 'province_name': province.name})
    coordinates = sorted(coordinates, key=lambda item: item['x'])

    adjacencies = set()
    for i in range(len(coordinates) - 1):
        upper_x = coordinates[i]['x'] + PROVINCE_BORDER_MARGIN
        lower_y, upper_y = coordinates[i]['y'] - PROVINCE_BORDER_MARGIN, coordinates[i]['y'] + PROVINCE_BORDER_MARGIN

        for j in range(i + 1, len(coordinates) - 1):
            if coordinates[j]['x'] > upper_x:
                # Out of x-scope
                break

            if coordinates[i]['province_name'] == coordinates[j]['province_name']:
                # Province doesn't border itself
                continue

            if lower_y < coordinates[j]['y'] < upper_y:
                adjacencies.add((coordinates[i]['province_name'], coordinates[j]['province_name']))

    return adjacencies


if __name__ == '__main__':
    # TODO: clean up & provide type safety & comment code
    # TODO: rig this up to the adjudicator!
    # TODO: rig this up to the bot!
    # TODO: GM state corrections
    # TODO: personal move map
    parse_map_data()
