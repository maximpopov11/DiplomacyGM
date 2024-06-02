# SVG map path
# Province border coordinates must be relative to the last coordinate and in the format x,y in the path string.
SVG_PATH = 'assets/imperial_diplomacy.svg'

# You can find the following in the SVG file. If you are using Inkscape, you will likely find id="..." next to
# inkscape:groupmode="layer" and inkscape:label="...", the latter of which may describe which of the following (if any)
# the group represents. Replace the strings below with the "..." contents of id="...".

# Layer group in SVG containing land province color fills
LAND_PROVINCE_FILL_LAYER_ID = 'layer6'
# Layer group in SVG containing sea province borders
SEA_PROVINCE_BORDER_LAYER_ID = 'layer8'
# Layer group in SVG containing province names
PROVINCE_NAMES_LAYER_ID = 'layer1'
# Layer group in SVG containing supply centers
SUPPLY_CENTER_LAYER_ID = 'layer3'
# Layer group in SVG containing units
UNITS_LAYER_ID = 'layer10'

# Margin of error for distance between province border points. If two province borders have a point within distance of
# this value in both x and y values, they will be considered adjacent.
PROVINCE_BORDER_MARGIN = 1
