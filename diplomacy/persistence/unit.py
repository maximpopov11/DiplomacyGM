from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diplomacy.persistence.player import Player
    from diplomacy.persistence.province import Province, Coast, Location
    from diplomacy.persistence.order import UnitOrder


class UnitType(Enum):
    ARMY = 1
    FLEET = 2


unit_type_to_name = {
    UnitType.ARMY: "A",
    UnitType.FLEET: "F",
}


class Unit:
    def __init__(
        self,
        unit_type: UnitType,
        player: Player,
        province: Province,
        coast: Coast | None,
        retreat_options: set[Province] | None,
        order: UnitOrder | None = None,
    ):
        self.unit_type: UnitType = unit_type
        self.player: Player = player
        self.province: Province = province
        self.coast: Coast | None = coast
        "retreat_options is None when not dislodged and {} when dislodged without retreat options"
        self.retreat_options: set[Province] | None = retreat_options
        self.order: UnitOrder | None = order

    def __str__(self):
        return f"{unit_type_to_name[self.unit_type]} {self.get_location()}"

    def get_location(self) -> Location:
        if self.coast:
            return self.coast
        return self.province

    def get_coordinate(self) -> tuple[float, float]:
        province = self.province
        if self.coast:
            if self.retreat_options is not None:
                return self.coast.retreat_unit_coordinate
            else:
                return self.coast.primary_unit_coordinate
        else:
            if self.retreat_options is not None:
                return province.retreat_unit_coordinate
            else:
                return province.primary_unit_coordinate
