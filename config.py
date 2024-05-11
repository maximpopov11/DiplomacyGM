PROVINCES_IMAGE = "assets/provinces.png"
CENTERS_IMAGE = "assets/centers.png"
ARMIES_IMAGE = "assets/armies.png"
FLEETS_IMAGE = "assets/fleets.png"

BORDER_COLOR = [0, 0, 0, 255]

# Include oceans, impassables, neutrals, and all players
PROVINCE_COLOR_TYPE_MAP = {
    (0, 38, 255): "ocean",
    (0, 255, 33): "green",
    (255, 0, 0): "red",
}

# Include separate colors (at least 1 RGB value off) for armies and fleets for all players
UNIT_COLOR_TYPE_MAP = {
    (182, 255, 0): "green",
    (255, 0, 221): "red",
}
