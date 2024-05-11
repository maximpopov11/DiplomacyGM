import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.segmentation import expand_labels, find_boundaries

from config import *


def read_map_data():
    provinces_image = np.asarray(Image.open(PROVINCES_IMAGE).convert('RGBA'))
    centers_image = np.asarray(Image.open(CENTERS_IMAGE).convert('RGBA'))
    armies_image = np.asarray(Image.open(ARMIES_IMAGE).convert('RGBA'))
    fleets_image = np.asarray(Image.open(FLEETS_IMAGE).convert('RGBA'))

    province_id_map, num_provinces = ndimage.label((provinces_image != BORDER_COLOR).any(-1), structure=np.ones((3, 3)))
    province_id_map_expanded = expand_labels(province_id_map, distance=6)

    adjacencies = get_adjacencies(province_id_map_expanded, num_provinces)
    province_owners = get_province_owners(provinces_image, province_id_map, num_provinces)
    centers = get_centers(province_id_map, centers_image)
    armies = get_units(province_id_map, armies_image)
    fleets = get_units(province_id_map, fleets_image)


def get_adjacencies(province_id_map_expanded, num_provinces):
    adjacencies = {}

    for province_id in range(1, num_provinces + 1):
        boundaries = find_boundaries(province_id_map_expanded == province_id, mode='outer')
        adjacencies[province_id] = np.setdiff1d(np.unique(province_id_map_expanded * boundaries), [0])

    return adjacencies


def get_province_owners(provinces, province_id_map, num_provinces):
    province_owners = {}

    for province_id in range(1, num_provinces + 1):
        colors, frequency = np.unique(provinces[province_id_map == province_id], return_counts=True, axis=0)
        if len(colors) != 1:
            print(f"Province #{province_id} is not one solid color: {colors} with frequency: {frequency}.")

        top_color = tuple(colors[np.argmax(frequency)][:3])
        assert top_color in PROVINCE_COLOR_TYPE_MAP, \
            f"{top_color} is not in the color to province type dictionary (province #{province_id})."
        province_owners[province_id] = PROVINCE_COLOR_TYPE_MAP[top_color]

    return province_owners


def get_centers(province_id_map, centers_image):
    # TODO: check majority province
    return set(np.setdiff1d(np.unique(province_id_map * (centers_image[:, :, 3] != 0)), [0]))


# Requires separate calls per unit type (armies, fleets)
def get_units(province_id_map, units_image):
    units = {}

    unit_id_map, num_units = ndimage.label((units_image[:, :, 3] != 0), structure=np.ones((3, 3)))
    for unit_id in range(1, num_units + 1):
        # TODO: check majority province
        province_ids, frequency = np.unique(province_id_map[unit_id_map == unit_id], return_counts=True)
        province_id = province_ids[frequency.argmax()]

        unit_colors = np.unique(units_image[unit_id_map == unit_id], axis=0)
        unit_player = None
        for color in unit_colors:
            color = tuple(color[:3])
            if color in UNIT_COLOR_TYPE_MAP:
                unit_player = UNIT_COLOR_TYPE_MAP[color]
                break
        assert unit_player is not None, f"Could not find player for unit {unit_id} with colors {unit_colors}"
        units[province_id] = {"unit_number": unit_id, "player": unit_player}

    return units


if __name__ == '__main__':
    read_map_data()
    # TODO: Adjudicate
    # TODO: Draw Results
    # TODO: Draw Orders
    # TODO: Support SVG
    # TODO: Read Province Names
    # TODO: Input Orders via Bot
    # TODO: View Preliminary Orders via Bot
    # TODO: Adjudicate via Bot
    # TODO: Output as Layers for GM Corrections
    # TODO: GM Corrections Commands
