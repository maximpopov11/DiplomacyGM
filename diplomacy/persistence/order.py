from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence.province import Location

if TYPE_CHECKING:
    from diplomacy.persistence.unit import Unit, UnitType, unit_type_to_name


class Order:
    """Order is a player's game state API."""

    def __init__(self):
        pass


# moves, holds, etc.
class UnitOrder(Order):
    """Unit orders are orders that units execute themselves."""

    def __init__(self):
        super().__init__()


class ComplexOrder(UnitOrder):
    """Complex orders are orders that operate on other orders (supports and convoys)."""

    def __init__(self, source: Unit):
        super().__init__()
        self.source: Unit = source


class Hold(UnitOrder):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "Holds"


class Core(UnitOrder):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "Cores"


class Move(UnitOrder):
    def __init__(self, destination: Location):
        super().__init__()
        self.destination: Location = destination

    def __str__(self):
        return f"- {self.destination}"


class ConvoyMove(UnitOrder):
    def __init__(self, destination: Location):
        super().__init__()
        self.destination: Location = destination

    def __str__(self):
        return f"Convoys - {self.destination}"


class ConvoyTransport(ComplexOrder):
    def __init__(self, source: Unit, destination: Location):
        super().__init__(source)
        self.destination: Location = destination

    def __str__(self):
        return f"Convoys {self.source.province} - {self.destination}"


class Support(ComplexOrder):
    def __init__(self, source: Unit, destination: Location):
        super().__init__(source)
        self.destination: Location = destination

    def __str__(self):
        suffix = "to Hold"
        if self.source.province != self.destination:
            suffix = f"- {self.destination}"
        return f"Supports {self.source.province} {suffix}"


class RetreatMove(UnitOrder):
    def __init__(self, destination: Location):
        super().__init__()
        self.destination: Location = destination

    def __str__(self):
        return f"- {self.destination}"


class RetreatDisband(UnitOrder):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return f"Disbands"


# TODO: (ALPHA) what if a player wants to change their build order? need to be able to remove build/disband orders
class PlayerOrder(Order):
    """Player orders are orders that belong to a player rather than a unit e.g. builds."""

    def __init__(self, location: Location):
        super().__init__()
        self.location: Location = location


class Build(PlayerOrder):
    """Builds are player orders because the unit does not yet exist."""

    def __init__(self, location: Location, unit_type: UnitType):
        super().__init__(location)
        self.unit_type: UnitType = unit_type

    def __str__(self):
        return f"Build {unit_type_to_name[self.unit_type]} {self.location}"


class Disband(PlayerOrder):
    """Disbands are player order because builds are."""

    def __init__(self, location: Location):
        super().__init__(location)

    def __str__(self):
        return f"Disband {self.location}"
