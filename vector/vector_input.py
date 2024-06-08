from lxml import etree
from shapely.geometry import Point, Polygon

from vector.config import *
from vector.province import Province

NAMESPACE = {'svg': 'http://www.w3.org/2000/svg'}


# Parse provinces, adjacencies, centers, and units
def parse_map_data():
    provinces_data, names_data, centers_data, units_data = get_svg_data()
    provinces = get_provinces(provinces_data, names_data, centers_data, units_data)
    adjacencies = get_adjacencies(provinces)


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
    provinces = create_provinces(provinces_data)
    initialize_province_names(provinces, names_data)
    initialize_supply_centers(provinces, centers_data)
    initialize_units(provinces, units_data)
    return provinces


# Creates provinces with border coordinates
def create_provinces(provinces_data):
    provinces = []
    for province in provinces_data:
        path = province.get('d')
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

        provinces.append(Province(province_coordinates))

    return provinces


# Sets province names
def initialize_province_names(provinces, names_data):
    def get_x(name_data):
        return name_data.get('x')

    def get_y(name_data):
        return name_data.get('y')

    def set_province_name(province, name_data):
        province.set_name(name_data.findall('.//svg:tspan', namespaces=NAMESPACE)[0].text)

    initialize_province_resident_data(provinces, names_data, get_x, get_y, set_province_name)


# Sets province supply center values
def initialize_supply_centers(provinces, centers_data):
    def get_x(supply_center_data):
        return supply_center_data.get('cx')

    def get_y(supply_center_data):
        return supply_center_data.get('cy')

    def set_province_supply_center(province, _):
        province.set_has_supply_center(True)

    initialize_province_resident_data(provinces, centers_data, get_x, get_y, set_province_supply_center)


# Sets province unit values
def initialize_units(provinces, units_data):
    def get_x(unit_data):
        return unit_data.findall('.//svg:path', namespaces=NAMESPACE)[0].get('d').split()[1].split(',')[0]

    def get_y(unit_data):
        return unit_data.findall('.//svg:path', namespaces=NAMESPACE)[0].get('d').split()[1].split(',')[1]

    def set_province_unit(province, unit_data):
        # TODO: The unit type is derived from shape which lives in sodipodi:type
        #  for which we might need to add sodipop to the namespace?
        unity_type = 'Lets pretend this is a unit type'
        # TODO: The player is derived from fill color lives in style below
        player = unit_data.findall('.//svg:path', namespaces=NAMESPACE)[0].get('style')
        province.set_unit({'type': unity_type, 'player': player})

    initialize_province_resident_data(provinces, units_data, get_x, get_y, set_province_unit)


# Initializes relevant province data
# resident_dataset: SVG element whose children each live in some province
# get_x and get_y: functions to get x and y child data in SVG
# function: method in Province that, given the province and a child element corresponding to that province, initializes
# that data in the Province
def initialize_province_resident_data(provinces, resident_dataset, get_x, get_y, function):
    resident_dataset = set(resident_dataset)
    for province in provinces:
        remove = set()

        polygon = Polygon(province.coordinates)
        for resident_data in resident_dataset:
            x = get_x(resident_data)
            y = get_y(resident_data)

            if not x or not y:
                remove.add(resident_data)
                continue

            point = Point((x, y))
            if polygon.contains(point):
                function(province, resident_data)
                remove.add(resident_data)

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
    # TODO: stop get adjacencies from crashing
    # TODO: provide print warning safety for titles, centers, units not found a home for
    # TODO: rig this up to the bot!
    parse_map_data()
