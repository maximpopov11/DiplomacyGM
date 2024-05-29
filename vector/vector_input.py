from lxml import etree
from shapely.geometry import Point, Polygon

from vector.config import *
from vector.province import Province


# Return:
# * Province list
# * Coordinate x,y,province dict sorted by x
def get_coordinates(province_data):
    provinces = []
    coordinates = []

    for province in province_data:
        province_name = province.get('name')
        path = province.get('d').split()

        province_coordinates = []
        for element in path:
            split = element.split(',')

            # Only accept data formatted x,y to ignore irrelevant SVG data
            if len(split) != 2:
                continue

            province_coordinates.append((float(split[0]), float(split[1])))

            coordinate = {'x': float(split[0]), 'y': float(split[1]), 'province': province_name}
            binary_insert(coordinate, coordinates)

        provinces.append(Province(province_name, province_coordinates))

    return provinces, coordinates


# Binary insert for coordinates by x
def binary_insert(coordinate, coordinates):
    left, right = 0, len(coordinates) - 1

    while left <= right:
        mid = (left + right) // 2
        if coordinates[mid]['x'] < coordinate['x']:
            left = mid + 1
        else:
            right = mid - 1

    coordinates.insert(left, coordinate)


# Return set of names of provinces with centers
def get_centers(provinces, center_data):
    center_coordinates = []
    for center in center_data:
        center_coordinates.append((center.get('cx'), center.get('cy')))

    centers = set()
    for province in provinces:
        polygon = Polygon(province.coordinates)

        for center in center_coordinates:
            point = Point(center)
            if polygon.contains(point):
                centers.add(province.get('name'))
                center_coordinates.remove(center)

    return centers


# Return province adjacency set
def get_adjacencies(coordinates):
    adjacencies = set()

    for i in range(len(coordinates) - 1):
        upper_x = coordinates[i]['x'] + 1
        lower_y, upper_y = coordinates[i]['y'] - 1, coordinates[i]['y'] + 1

        for j in range(i + 1, len(coordinates) - 1):
            if coordinates[j]['x'] > upper_x:
                # Out of x-scope
                break

            if coordinates[i]['province'] == coordinates[j]['province']:
                # Province doesn't border itself
                continue

            if lower_y < coordinates[j]['y'] < upper_y:
                adjacencies.add((coordinates[i]['province'], coordinates[j]['province']))

    return adjacencies


# Parse provinces, adjacencies, centers, and units
def parse_map_data():
    map_data = etree.parse(SVG)
    provinces_data = map_data.xpath(f'//*[@id="{PROVINCE_LAYER_ID}"]')[0].getchildren()
    centers_data = map_data.xpath(f'//*[@id="{CENTER_LAYER_ID}"]')[0].getchildren()

    provinces, coordinates = get_coordinates(provinces_data)
    centers = get_centers(provinces, centers_data)
    adjacencies = get_adjacencies(coordinates)


if __name__ == '__main__':
    parse_map_data()
    # TODO: we don't get coordinates right actually evidenced by polygon not finding center
