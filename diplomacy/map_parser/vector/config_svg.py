# SVG map path
# Province border coordinates must be relative to the last coordinate and in the format x,y in the path string.
SVG_PATH: str = "assets/imperial_diplomacy.svg"

# You can find the following in the SVG file. If you are using Inkscape, you will likely find id="..." next to
# inkscape:groupmode="layer" and inkscape:label="...", the latter of which may describe which of the following (if any)
# the group represents. Replace the strings below with the "..." contents of id="...".

# Layer group in SVG containing land province color fills
LAND_PROVINCE_LAYER_ID: str = "layer6"
# Layer group in SVG containing island rings
ISLAND_RING_LAYER_ID: str = "layer9"
# Layer group in SVG containing island province color fills
ISLAND_FILL_PLAYER_ID: str = "layer11"
# Layer group in SVG containing island province borders
ISLAND_PROVINCE_LAYER_ID: str = "layer5"
# Layer group in SVG containing sea province borders
SEA_PROVINCE_LAYER_ID: str = "layer2"
# Layer group in SVG containing province names
PROVINCE_NAMES_LAYER_ID: str = "layer1"
# Layer group in SVG containing supply centers
SUPPLY_CENTER_LAYER_ID: str = "layer3"
# Layer group in SVG containing units
UNITS_LAYER_ID: str = "layer10"

# Layer groups in SVG containing phantom units for optimal unit placements
PHANTOM_PRIMARY_ARMY_LAYER_ID: str = "g652"
PHANTOM_RETREAT_ARMY_LAYER_ID: str = "g2176"
PHANTOM_PRIMARY_FLEET_LAYER_ID: str = "layer15"
PHANTOM_RETREAT_FLEET_LAYER_ID: str = "g3300"

# If the province fills are labeled directly on the SVG we can guarantee 100% accuracy on naming the provinces
PROVINCE_FILLS_LABELED: bool = True
# If the center provinces are labeled directly on the SVG we can guarantee 100% accuracy on matching center to province
CENTER_PROVINCES_LABELED: bool = True
# If the unit provinces are labeled directly on the SVG we can guarantee 100% accuracy on matching unit to province
UNIT_PROVINCES_LABELED: bool = True

# Margin of error for distance between province border points. If two province borders have a point within distance of
# this value in both x and y values, they will be considered adjacent.
PROVINCE_BORDER_MARGIN: float = 5
