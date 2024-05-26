from xml.dom import minidom

if __name__ == '__main__':
    svg = minidom.parse('assets/test.svg')
    path_strings = [path.getAttribute('d') for path in svg.getElementsByTagName('path')]
    svg.unlink()
    # TODO: parse provinces
        # TODO: populate territories
        # TODO: populate province coordinates twice sorted x and y globally w/ province match
        # TODO: record centers
    # TODO: parse adjacencies
        # TODO: iterate through coordinate windows and add to set all in range of a point's x and y
    # TODO: parse players
    # TODO: parse units
