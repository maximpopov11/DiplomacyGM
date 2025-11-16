from enum import Enum

from diplomacy.persistence.order import NMR, Hold, Core, Move, ConvoyMove, Support, ConvoyTransport
from diplomacy.persistence.province import Province, Location, Coast
from diplomacy.persistence.unit import Unit, UnitType


class Resolution(Enum):
    SUCCEEDS = 0
    FAILS = 1


class ResolutionState(Enum):
    UNRESOLVED = 0
    GUESSING = 1
    RESOLVED = 2


class OrderType(Enum):
    HOLD = 0
    CORE = 1
    MOVE = 2
    SUPPORT = 3
    CONVOY = 4


class AdjudicableOrder:
    def __init__(self, unit: Unit):
        self.state = ResolutionState.UNRESOLVED
        self.resolution = Resolution.FAILS

        if unit.order is None:
            raise ValueError(f"Order for unit {unit} is missing")

        self.country = unit.player
        self.is_army = unit.unit_type == UnitType.ARMY
        self.current_province = unit.province

        self.supports: set[AdjudicableOrder] = set()
        self.convoys: set[AdjudicableOrder] = set()

        self.type: OrderType
        self.destination_province: Province = self.current_province
        self.raw_destination: Location = self.current_province
        self.source_province: Province = self.current_province
        self.is_convoy: bool = False
        # indicates that a move is also a convoy that failed, so no support holds
        self.not_supportable = False
        self.is_valid = True
        if isinstance(unit.order, Hold) or isinstance(unit.order, NMR):
            self.type = OrderType.HOLD
        elif isinstance(unit.order, Core):
            self.type = OrderType.CORE
        elif isinstance(unit.order, Move) or isinstance(unit.order, ConvoyMove):
            self.type = OrderType.MOVE
            self.destination_province = unit.order.destination.as_province()
            self.raw_destination = unit.order.destination
            if isinstance(unit.order, ConvoyMove):
                self.is_convoy = True
        elif isinstance(unit.order, Support):
            self.type = OrderType.SUPPORT
            self.source_province = unit.order.source.as_province()
            self.destination_province = unit.order.destination.as_province()
            self.raw_destination = unit.order.destination
        elif isinstance(unit.order, ConvoyTransport):
            self.type = OrderType.CONVOY
            self.source_province = unit.order.source.as_province()
            self.destination_province = unit.order.destination.as_province()
            self.raw_destination = unit.order.destination
        else:
            raise ValueError(f"Can't parse {unit.order.__class__.__name__} to OrderType")

        self.base_unit = unit

    def __str__(self):
        # This could be improved
        return f"{self.current_province} {self.type} {self.destination_province} [{self.state}:{self.resolution}]"