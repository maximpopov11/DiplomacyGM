import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.segmentation import expand_labels, find_boundaries

PROVINCES_IMAGE = "assets/provinces.png"
CENTERS_IMAGE = "assets/centers.png"

BORDER_COLOR = [0, 0, 0, 255]

COLOR_PROVINCE_TYPE_MAP = {
    (96, 96, 96, 255): "impassable",
    (197, 223, 234, 255): "ocean",
    (196, 143, 133, 255): "brown",
    (255, 56, 50, 255): "red",
    (255, 203, 91, 255): "yellow",
}


def read_map_data():
    provinces_image = np.asarray(Image.open(PROVINCES_IMAGE).convert('RGBA'))
    centers_image = np.asarray(Image.open(CENTERS_IMAGE).convert('RGBA'))

    province_id_map, num_provinces = ndimage.label((provinces_image != BORDER_COLOR).any(-1), structure=np.ones((3, 3)))
    province_id_map_expanded = expand_labels(province_id_map, distance=6)

    adjacencies = get_adjacencies(province_id_map_expanded, num_provinces)
    province_owners = get_province_owners(provinces_image, province_id_map, num_provinces)
    centers = get_centers(province_id_map, centers_image)


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

        top_color = colors[np.argmax(frequency)]
        assert tuple(top_color) in COLOR_PROVINCE_TYPE_MAP, \
            f"{tuple(top_color)} is not in the color to province type dictionary (province #{province_id})."
        province_owners[province_id] = COLOR_PROVINCE_TYPE_MAP[tuple(top_color)]

    return province_owners


def get_centers(province_id_map, centers_image):
    return set(np.setdiff1d(np.unique(province_id_map * (centers_image[:, :, 3] != 0)), [0]))


if __name__ == '__main__':
    read_map_data()
