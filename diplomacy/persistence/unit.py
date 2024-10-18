from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diplomacy.persistence import player
    from diplomacy.persistence import province
    from diplomacy.persistence import order


# TODO: rename to Type and import as unit.Type
class UnitType(Enum):
    ARMY = "A"
    FLEET = "F"


class Unit:
    def __init__(
        self,
        unit_type: UnitType,
        owner: player.Player,
        current_province: province.Province,
        coast: province.Coast | None,
        retreat_options: set[province.Province] | None,
    ):
        self.unit_type: UnitType = unit_type
        self.player: player.Player = owner
        self.province: province.Province = current_province
        self.coast: province.Coast | None = coast

        # retreat_options is None when not dislodged and {} when dislodged without retreat options
        self.retreat_options: set[province.Province] | None = retreat_options
        self.order: order.UnitOrder | None = None

    def __str__(self):
        return f"{self.unit_type.value} {self.location()}"

    def location(self) -> province.Location:
        if self.coast:
            return self.coast
        return self.province
