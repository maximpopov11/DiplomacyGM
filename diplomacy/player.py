from typing import Set

from diplomacy.province import Province
from diplomacy.unit import Unit


class Player:
    def __init__(self, name: str, centers: Set[Province], units: Set[Unit]):
        self.name: str = name
        self.centers: Set[Province] = centers
        self.units: Set[Unit] = units
