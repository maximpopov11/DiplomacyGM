import re
from abc import abstractmethod
from xml.etree.ElementTree import Element


class Transform:
    def __init__(self, element: Element):
        self.transform_string = element.get("transform", None)

    @abstractmethod
    def transform(self, point: tuple[float, float]) -> tuple[float, float]:
        pass


class Translation(Transform):
    def __init__(self, element: Element):
        super().__init__(element)
        translation_match = re.search("^\\s*translate\\((.*),(.*)\\)\\s*", self.transform_string)

        self.x, self.y = 0, 0
        if translation_match:
            self.x = float(translation_match.group(1))
            self.y = float(translation_match.group(2))
        else:
            raise RuntimeError("Translation not found")

    def transform(self, point: tuple[float, float]) -> tuple[float, float]:
        return point[0] + self.x, point[1] + self.y


class MatrixTransform(Transform):
    def __init__(self, element: Element):
        super().__init__(element)
        matrix_transform_match = re.search("^\\s*matrix\\((.*),(.*),(.*),(.*),(.*),(.*)\\)\\s*", self.transform_string)

        self.x_dx, self.y_dy = 1, 1
        self.y_dx, self.x_dy, x_c, y_x = 0, 0, 0, 0
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
        x = self.x_dx * point[0] + self.y_dx * point[1] + self.x_c
        y = self.x_dy * point[0] + self.y_dy * point[1] + self.y_c
        return x, y
