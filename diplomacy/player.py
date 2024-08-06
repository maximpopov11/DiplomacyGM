from __future__ import annotations

from typing import Set, TYPE_CHECKING

if TYPE_CHECKING:
    from diplomacy.province import Province
    from diplomacy.unit import Unit


class Player:
    def __init__(self, name: str):
        self.name: str = name
        self.centers: Set[Province] = []
        self.units: Set[Unit] = []

    def add_center(self, center: Province):
        self.centers.add(center)

    def add_unit(self, unit: Unit):
        self.units.add(unit)
