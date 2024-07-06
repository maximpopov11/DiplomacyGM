import matplotlib.pyplot as plt


# Debugging tool to visualize which province corresponds to which id
def draw_provinces_by_id(labels):
    _, ax = plt.subplots()
    ax.imshow(labels, cmap=plt.cm.gray, vmin=0, vmax=1)
    plt.show()
