from lxml import etree

if __name__ == '__main__':
    map_data = etree.parse('assets/test.svg')

    provinces = map_data.xpath('//*[@id="layer10"]')[0].getchildren()
    coordinates = {}
    for province in provinces:
        province_id = province.get('id')
        if not coordinates.get(province_id):
            coordinates[province_id] = []

        path = province.get('d').split()
        for element in path:
            split = element.split(',')
            if len(split) != 2:
                continue
            coordinates.get(province_id).append((split[0], split[1]))

    # TODO: parse provinces
        # TODO: populate territories
        # TODO: populate province coordinates twice sorted x and y globally w/ province match
        # TODO: record centers
    # TODO: parse adjacencies
        # TODO: iterate through coordinate windows and add to set all in range of a point's x and y
    # TODO: parse players
    # TODO: parse units
