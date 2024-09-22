from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence import order

if TYPE_CHECKING:
    from diplomacy.persistence.province import Province
    from diplomacy.persistence.unit import Unit


class Player:
    def __init__(self, name: str, color: str, vscc: int, centers: set[Province], units: set[Unit]):
        self.name: str = name
        self.color: str = color
        self.centers: set[Province] = centers
        self.units: set[Unit] = units
        self.vscc: int = vscc

        self.build_orders: set[order.PlayerOrder] = set()

    def __str__(self):
        return self.name
