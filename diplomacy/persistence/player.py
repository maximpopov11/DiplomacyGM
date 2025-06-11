from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence import order

from enum import Enum

if TYPE_CHECKING:
    from diplomacy.persistence import province
    from diplomacy.persistence import unit

class VassalType(Enum):
    '''Needed due to ambiguity, especially after fall moves but before fall retreats'''
    VASSAL = 'vassal'
    DUAL = 'dual'

class Player:
    def __init__(
        self,
        name: str,
        color: str,
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

        # victory supply center count (we assume VSCC scoring)
        self.vscc: int = vscc
        # initial supply center count
        self.iscc: int = iscc

        self.centers: set[province.Province] = centers
        self.units: set[unit.Unit] = units

        self.build_orders: set[order.PlayerOrder] = set()

        self.points: int = 0
        self.liege: Player | None = None
        self.discord_id = None
        self.vassels: list[Player] = []

    def __str__(self):
        return self.name

    def score(self):
        if len(self.centers) > self.iscc:
            return (len(self.centers) - self.iscc) / (self.vscc - self.iscc)
        else:
            return (len(self.centers) / self.iscc) - 1
