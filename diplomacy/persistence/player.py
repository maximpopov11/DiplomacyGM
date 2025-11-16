from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence import order

from enum import Enum

if TYPE_CHECKING:
    from diplomacy.persistence import province
    from diplomacy.persistence import unit


class VassalType(Enum):
    """Needed due to ambiguity, especially after fall moves but before fall retreats"""

    VASSAL = "vassal"
    DUAL = "dual"


class PlayerClass(Enum):
    DUCHY = 0
    KINGDOM = 1
    EMPIRE = 2


class Player:
    def __init__(
        self,
        name: str,
        color: str,
        win_type: str,
        vscc: int,
        iscc: int,
        centers: set[province.Province],
        units: set[unit.Unit],
    ):
        self.name: str = name
        self.color_dict: dict | None = None
        # color used for rendering vs internal default color
        if isinstance(color, dict):
            self.color_dict = color
            self.default_color = color["standard"]
            self.render_color = color["standard"]
        else:
            self.color_dict = None
            self.default_color = color
            self.render_color = color

        self.win_type = win_type
        # victory supply center count
        self.vscc: int = vscc
        # initial supply center count
        self.iscc: int = iscc

        self.centers: set[province.Province] = centers
        self.units: set[unit.Unit] = units

        self.build_orders: set[order.PlayerOrder] = set()
        self.waived_orders: int = 0

        self.vassal_orders: dict[Player, order.RelationshipOrder] = {}

        self.points: int = 0
        self.liege: Player | None = None
        self.discord_id = None
        self.vassals: list[Player] = []

    def __str__(self):
        return self.name

    def info(self, variant: str = "standard") -> str:
        bullet = "\n- "

        units = list(sorted(self.units, key=lambda u: (u.unit_type.value, u.location().name)))
        centers = list(sorted(self.centers, key=lambda c: c.name))
        
        if variant == "chaos":
            out = (
                f"Color: #{self.render_color}\n"
                + f"Points: {self.points}\n"
                + f"Vassals: {', '.join(map(str,self.vassals))}\n"
                + f"Liege: {self.liege if self.liege else 'None'}\n"
                + f"Units ({len(units)}): {(bullet + bullet.join([unit.location().name for unit in units])) if len(units) > 0 else 'None'}\n"
                + f"Centers ({len(centers)}): {(bullet + bullet.join([center.name for center in centers])) if len(centers) > 0 else 'None'}\n"
            )
            return out

        center_str = "Centers:"
        for center in centers:
            center_str += bullet
            if center.core == self:
                center_str += f"{center.name} (core)"
            elif center.half_core == self:
                center_str += f"{center.name} (half-core)"
            else:
                center_str += f"{center.name}"

        unit_str = "Units:"
        for unit in units:
            unit_str += f"{bullet}({unit.unit_type.value}) {unit.location().name}"
            
        out = (
            ""
            + f"Color: {(bullet + bullet.join([k + ': ' + v for k, v in self.color_dict.items()]) if self.color_dict is not None else self.render_color)}\n"
            + f"Score: [{len(self.centers)}/{self.vscc}] {round(self.score() * 100, 2)}%\n"
            + f"{center_str}\n"
            + f"{unit_str}\n"
        )


        
        return out

    def score(self):
        if self.win_type == "classic":
            return (len(self.centers) / self.vscc)
        if len(self.centers) > self.iscc:
            return (len(self.centers) - self.iscc) / (self.vscc - self.iscc)
        else:
            return (len(self.centers) / self.iscc) - 1

    def get_class(self) -> PlayerClass:
        scs = len(self.centers)
        if scs >= 6:
            return PlayerClass.EMPIRE
        elif scs >= 3:
            return PlayerClass.KINGDOM
        else:
            return PlayerClass.DUCHY
