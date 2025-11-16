import re
from xml.etree.ElementTree import Element
import numpy as np

class TransGL3:
    def __init__(self, transform_string: str | Element | None=None):
        if transform_string is None:
            transform_string = ""
        if not isinstance(transform_string, str):
            transform_string = transform_string.get("transform", "")
        
        x_dx = 1
        y_dy = 1
        x_dy = 0
        y_dx = 0
        x_c = 0
        y_c = 0
        transform_string = transform_string.strip()

        if transform_string.startswith("matrix"):
            match = re.search(r"matrix\((.*),(.*),(.*),(.*),(.*),(.*)\)", transform_string)
            x_dx = float(match.group(1))
            y_dx = float(match.group(2))
            x_dy = float(match.group(3))
            y_dy = float(match.group(4))
            x_c = float(match.group(5))
            y_c = float(match.group(6))

        elif transform_string.startswith("translate"):
            match = re.search(r"translate\((.*),(.*)\)", transform_string)
            x_c = float(match.group(1))
            y_c = float(match.group(2))
        elif transform_string.startswith("rotate"):
            match = re.search(r"rotate\((.*),(.*),(.*)\)", transform_string)
            if not match:
                match = re.search(r"rotate\((.*)\)", transform_string)
                coord = 0, 0
            else:
                coord = float(match.group(2)), float(match.group(3))
            angle = float(match.group(1)) * np.pi / 180
            pre = TransGL3().init(x_c=-coord[0], y_c=-coord[1])
            post = TransGL3().init(x_c=coord[0], y_c=coord[1])
            cos = np.cos(angle)
            sin = np.sin(angle)
            x_dx =  cos
            y_dx =  sin
            x_dy = -sin
            y_dy =  cos

        elif transform_string != "":
            raise Exception(f"Unknown transformation: {transform_string}")
        
        # the matrix represents the transformation from (x, y, const) to (x, y const)
        # we preserve the const via a 1 so that convolutions work correctly
        self.matrix = np.array([
            [x_dx, y_dx, 0],
            [x_dy, y_dy, 0],
            [x_c , y_c , 1]
        ])
        if transform_string.startswith("rotate"):
            self.matrix = pre.matrix @ self.matrix @ post.matrix

    # this is so that functions can create TransGL3 with specific values, not from an element
    def init(self, x_dx=1, y_dy=1, x_dy=0, y_dx=0, x_c=0, y_c=0):
        self.matrix = np.array([
            [x_dx, y_dx, 0],
            [x_dy, y_dy, 0],
            [x_c , y_c , 1]
        ])
        return self

    def transform(self, point: tuple[float, float]) -> tuple[float, float]:
        point = np.concatenate((point, (1,)))
        return tuple((point @ self.matrix)[:2].tolist())

    # represents a convolution
    # (t1 * t2).transform(p) == t1.transform(t2.transform(p))
    def __mul__(self, other):
        out = TransGL3()
        out.matrix = self.matrix @ other.matrix
        return out

    def __str__(self):
        return f"matrix({','.join(map(str, self.matrix[:, :2].flatten()))})"
