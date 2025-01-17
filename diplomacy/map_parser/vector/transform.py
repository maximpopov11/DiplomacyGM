import re
from abc import abstractmethod
from xml.etree.ElementTree import Element
import numpy as np

class Transform:
    def __init__(self, element: Element):
        self.transform_string: str | None = element.get("transform", None)

    @abstractmethod
    def transform(self, point: tuple[float, float]) -> tuple[float, float]:
        pass

    @abstractmethod
    def inverse_transform(self, point: tuple[float, float]) -> tuple[float, float]:
        pass


class EmptyTransform(Transform):
    def __init__(self, element: Element):
        super().__init__(element)

    def transform(self, point: tuple[float, float]) -> tuple[float, float]:
        return point
    
    def inverse_transform(self, point):
        return point
    
    def __str__(self):
        return ""


class Translation(Transform):
    def __init__(self, element: Element, data=None):
        if data != None:
            # just set it to this value
            print(type(data[0]))
            assert(not isinstance(data, str))
            self.x = data[0]
            self.y = data[1]
            return

        super().__init__(element)
        self.x, self.y = 0, 0

        if self.transform_string:
            translation_match = re.search("^\\s*translate\\((.*),(.*)\\)\\s*", self.transform_string)
            if translation_match:
                self.x = float(translation_match.group(1))
                self.y = float(translation_match.group(2))
            else:
                raise RuntimeError("Translation not found")

    def transform(self, point: tuple[float, float]) -> tuple[float, float]:
        return point[0] + self.x, point[1] + self.y

    def inverse_transform(self, point):
        return point[0] - self.x, point[1] - self.y

    def __str__(self):
        return f"translate({self.x},{self.y})"

class MatrixTransform(Transform):
    def __init__(self, element: Element):
        super().__init__(element)
        self.x_dx, self.y_dy = 1, 1
        self.y_dx, self.x_dy, self.x_c, self.y_x = 0, 0, 0, 0

        if self.transform_string:
            matrix_transform_match = re.search(
                "^\\s*matrix\\((.*),(.*),(.*),(.*),(.*),(.*)\\)\\s*", self.transform_string
            )
            self.matrix_transform: tuple[float, float, float, float, float, float] = (1, 0, 0, 1, 0, 0)
            if matrix_transform_match:
                self.x_dx = float(matrix_transform_match.group(1))
                self.y_dx = float(matrix_transform_match.group(2))
                self.x_dy = float(matrix_transform_match.group(3))
                self.y_dy = float(matrix_transform_match.group(4))
                self.x_c = float(matrix_transform_match.group(5))
                self.y_c = float(matrix_transform_match.group(6))
            else:
                raise RuntimeError("Matrix transform not found")

    def transform(self, point: tuple[float, float]) -> tuple[float, float]:
        try:
            x = self.x_dx * point[0] + self.x_dy * point[1] + self.x_c
        except:
            import pdb
            pdb.set_trace()
        y = self.y_dx * point[0] + self.y_dy * point[1] + self.y_c
        return x, y

    def inverse_transform(self, point: tuple[float, float]) -> tuple[float, float]:
        x = point[0] - self.x_c
        y = point[1] - self.y_c
        matrix = np.array([[self.x_dx, self.y_dx], [self.x_dy, self.y_dy]])
        matrix = np.linalg.inv(matrix)
        return ((x, y) @ matrix).tolist()

    def __str__(self):
        return f"matrix({self.x_dx},{self.y_dx},{self.x_dy},{self.y_dy},{self.x_c},{self.y_c})"


def get_transform(element: Element) -> Transform:
    transform_string: str | None = element.get("transform", None)
    if not transform_string:
        return EmptyTransform(element)
    elif transform_string.startswith("translate"):
        return Translation(element)
    elif transform_string.startswith("matrix"):
        return MatrixTransform(element)
    else:
        raise RuntimeError(f"Unknown transform: {transform_string}")
