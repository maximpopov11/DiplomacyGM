from __future__ import annotations

from typing import TYPE_CHECKING

from diplomacy.persistence.province import Location, Coast

if TYPE_CHECKING:
    from diplomacy.persistence.unit import Unit, UnitType


class Order:
    """Order is a player's game state API."""

    def __init__(self):
        pass


# moves, holds, etc.
class UnitOrder(Order):
    """Unit orders are orders that units execute themselves."""
    display_priority: int = 0
    
    def __init__(self):
        super().__init__()
        self.hasFailed = False


class ComplexOrder(UnitOrder):
    """Complex orders are orders that operate on other orders (supports and convoys)."""

    def __init__(self, source: Location):
        super().__init__()
        self.source: Location = source

class NMR(UnitOrder):
    display_priority: int = 20

    def __init__(self):
        super().__init__()

    def __str__(self):
        return "NMRs"

class Hold(UnitOrder):
    display_priority: int = 20

    def __init__(self):
        super().__init__()

    def __str__(self):
        return "Holds"


class Core(UnitOrder):
    display_priority: int = 20
    
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "Cores"


class Move(UnitOrder):
    display_priority: int = 30
    
    def __init__(self, destination: Location):
        super().__init__()
        self.destination: Location = destination

    def __str__(self):
        return f"- {self.destination}"

class ConvoyMove(UnitOrder):
    display_priority: int = 30
    
    def __init__(self, destination: Location):
        super().__init__()
        self.destination: Location = destination

    def __str__(self):
        return f"Convoys - {self.destination}"


class ConvoyTransport(ComplexOrder):
    def __init__(self, source: Location, destination: Location):
        super().__init__(source)
        self.destination: Location = destination

    def __str__(self):
        return f"Convoys {self.source} - {self.destination}"


class Support(ComplexOrder):
    display_priority: int = 10
    
    def __init__(self, source: Location, destination: Location):
        super().__init__(source)
        self.destination: Location = destination

    def __str__(self):
        suffix = "Hold"

        destination_province = self.destination
        if isinstance(self.destination, Coast):
            destination_province = self.destination.province

        if self.source != destination_province:
            suffix = f"- {self.destination}"
        return f"Supports {self.source} {suffix}"


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


class PlayerOrder(Order):
    """Player orders are orders that belong to a player rather than a unit e.g. builds."""

    def __init__(self, location: Location):
        super().__init__()
        self.location: Location = location

    def __hash__(self):
        return hash(self.location.name)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.location.name == other.location.name


class Build(PlayerOrder):
    """Builds are player orders because the unit does not yet exist."""

    def __init__(self, location: Location, unit_type: UnitType):
        super().__init__(location)
        self.unit_type: UnitType = unit_type

    def __str__(self):
        return f"Build {self.unit_type.value} {self.location}"


class Disband(PlayerOrder):
    """Disbands are player order because builds are."""

    def __init__(self, location: Location):
        super().__init__(location)

    def __str__(self):
        return f"Disband {self.location}"

class Waive(Order):
    def __init__(self, quantity: int):
        super().__init__()
        self.quantity: int = quantity

    def __str__(self):
        return f"Waive {self.quantity}"

class RelationshipOrder(Order):
    """Vassal, Dual Monarchy, etc"""

    nameId: str = None

    def __init__(self, player: Player):
        super().__init__()
        self.player = player
    
    def __hash__(self):
        return hash(self.player)
    
    def __eq__(self, other):
        return isinstance(other, type(self)) and self.player == other.player

class Vassal(RelationshipOrder):
    """Specifies player to vassalize."""

    def __str__(self):
        return f"Vassalize {self.player}"

class Liege(RelationshipOrder):
    """Specifies player to swear allegiance to."""

    def __str__(self):
        return f"Liege {self.player}"

class DualMonarchy(RelationshipOrder):
    """Specifies player to swear allegiance to."""

    def __str__(self):
        return f"Dual Monarchy with {self.player}"

class Disown(RelationshipOrder):
    """Specifies player to drop as a vassal."""

    def __str__(self):
        return f"Disown {self.player}"

class Defect(RelationshipOrder):
    """Defect. Player is always your liege"""

    def __str__(self):
        return "Defect"

class RebellionMarker(RelationshipOrder):
    """Psudorder to mark rebellion from player due to class"""

    def __str__(self):
        return f"(Rebelling from {self.player})"