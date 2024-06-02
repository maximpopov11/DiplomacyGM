from lxml import etree
from shapely.geometry import Point, Polygon

from vector.config import *
from vector.province import Province


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


# TODO: can we share the geometry in the next 3 functions? Pass attribute to check, value to get, function to set
# Sets province names
def initialize_province_names(provinces, names_data):
    # TODO: get name
    namespace = {'svg': 'http://www.w3.org/2000/svg'}
    # names_data[0].findall('.//svg:tspan', namespaces=namespace)

    names = set(names_data)
    for province in provinces:
        polygon = Polygon(province.coordinates)

        for name in names:
            x = name.get('x')
            y = name.get('y')

            if not x or not y:
                names.remove(name)
                continue

            point = Point((x, y))
            if polygon.contains(point):
                province.set_name(name.get('id'))  # TODO: how do we access the name?
                names.remove(name)


# Sets province supply center values
def initialize_supply_centers(provinces, centers_data):
    centers = set(centers_data)

    for province in provinces:
        polygon = Polygon(province.coordinates)

        for center in centers:
            point = Point(center.get('cx'), center.get('cy'))
            if polygon.contains(point):
                province.set_center(True)
                centers.remove(center)


# Sets province unit values
def initialize_units(provinces, units_data):
    units = set(units_data)

    for province in provinces:
        polygon = Polygon(province.coordinates)

        for unit in units:
            point = Point(unit.get('cx'), unit.get('cy'))
            if polygon.contains(point):
                province.set_unit({'type': unit.get('type'), 'player': unit.get('color')})
                units.remove(unit)


# Returns province adjacency set
def get_adjacencies(provinces):
    coordinates = []
    for province in provinces:
        for coordinate in province.coordinates:
            coordinates.append({'x': coordinate[0], 'y': coordinate[1], 'province_name': province.name})
    coordinates = sorted(coordinates, key=lambda item: item[0][0])

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
    parse_map_data()
