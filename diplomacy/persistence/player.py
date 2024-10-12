from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence import order

if TYPE_CHECKING:
    from diplomacy.persistence.province import Province
    from diplomacy.persistence.unit import Unit


class Player:
    def __init__(self, name: str, color: str, vscc: int, start: int, centers: set[Province], units: set[Unit]):
        self.name: str = name
        self.color: str = color
        self.centers: set[Province] = centers
        self.units: set[Unit] = units
        self.vscc: int = vscc
        self.start: int = start

        self.build_orders: set[order.PlayerOrder] = set()

    def get_vscc(self):
        return (len(self.centers) - self.start) / (self.vscc - self.start)


    def __str__(self):
        return self.name
