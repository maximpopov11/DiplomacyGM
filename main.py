import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.segmentation import expand_labels, find_boundaries

MAP_IMAGE = "assets/provinces.png"

BORDER_COLOR = [0, 0, 0, 255]

COLOR_PROVINCE_TYPE_MAP = {
    (96, 96, 96, 255): "impassable",
    (197, 223, 234, 255): "ocean",
    (196, 143, 133, 255): "brown",
    (255, 56, 50, 255): "red",
    (255, 203, 91, 255): "yellow",
}


# Debugging tool to visualize which province corresponds to which id
def draw_provinces_by_id(labels):
    _, ax = plt.subplots()
    ax.imshow(labels, cmap=plt.cm.gray, vmin=0, vmax=1)
    plt.show()


if __name__ == '__main__':
    provinces = np.asarray(Image.open(MAP_IMAGE).convert('RGBA'))
    province_ids, num_provinces = ndimage.label((provinces != BORDER_COLOR).any(-1), structure=np.ones((3, 3)))
    province_ids_expanded = expand_labels(province_ids, distance=6)

    adjacencies = {}
    for province_id in range(1, num_provinces + 1):
        boundaries = find_boundaries(province_ids_expanded == province_id, mode='outer')
        adjacencies[province_id] = np.setdiff1d(np.unique(province_ids_expanded * boundaries), [0])

    province_owners = {}
    for province_id in range(1, num_provinces + 1):
        colors, frequency = np.unique(provinces[province_ids == province_id], return_counts=True, axis=0)
        if len(colors) != 1:
            print(f"Province #{province_id} is not one solid color: {colors} with frequency: {frequency}.")
        top_color = colors[np.argmax(frequency)]
        assert tuple(top_color) in COLOR_PROVINCE_TYPE_MAP, \
            f"{tuple(top_color)} is not in the color to province type dictionary (province #{province_id})."
        province_owners[province_id] = COLOR_PROVINCE_TYPE_MAP[tuple(top_color)]
