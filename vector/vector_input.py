from lxml import etree

from vector.config import *


# Return coordinate x,y,province list sorted by x
def get_coordinates(provinces):
    coordinates = []

    for province in provinces:
        province_name = province.get('name')
        path = province.get('d').split()

        for element in path:
            split = element.split(',')

            # Only accept data formatted x,y to ignore irrelevant SVG data
            if len(split) != 2:
                continue

            coordinate = {'x': float(split[0]), 'y': float(split[1]), 'province': province_name}
            binary_insert(coordinate, coordinates)

    return coordinates


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
    coordinates = get_coordinates(provinces_data)
    adjacencies = get_adjacencies(coordinates)


if __name__ == '__main__':
    parse_map_data()
