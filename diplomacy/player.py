from typing import Set

from diplomacy.unit import Unit


class Player:
    def __init__(self, name: str, units: Set[Unit]):
        self.name = name
        self.units = units
        pass
