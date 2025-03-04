from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence import order

if TYPE_CHECKING:
    from diplomacy.persistence import province
    from diplomacy.persistence import unit

class PlayerInfo:
    def __init__(
        self,
        name: str,
        color: str,
        vscc: int,
        iscc: int,
    ):
        self.name: str = name
        self.base_color: str = color

        # victory supply center count (we assume VSCC scoring)
        self.vscc: int = vscc
        # initial supply center count
        self.iscc: int = iscc

class Player:
    def __init__(
        self,
        info: PlayerInfo,
        centers: set[province.Province],
        units: set[unit.Unit],
    ):
        self.info = info
        self.color = self.info.base_color

        self.centers: set[province.Province] = centers
        self.units: set[unit.Unit] = units

        self.build_orders: set[order.PlayerOrder] = set()

    def __str__(self):
        return self.name()
    
    def name(self):
        return self.info.name

    def vscc(self):
        return self.info.vscc

    def iscc(self):
        return self.info.iscc



    def score(self):
        if len(self.centers) > self.info.iscc:
            return (len(self.centers) - self.info.iscc) / (self.info.vscc - self.info.iscc)
        else:
            return (len(self.centers) / self.info.iscc) - 1