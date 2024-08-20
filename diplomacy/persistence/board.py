from diplomacy.persistence.order import Order, UnitOrder
from diplomacy.persistence.phase import Phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.province import Province
from diplomacy.persistence.unit import Unit


class Board:
    def __init__(
        self,
        players: set[Player],
        provinces: set[Province],
        units: set[Unit],
        unit_orders: dict[Unit, Order],
        build_orders: set[Order],
        phase: Phase,
    ):
        self.players: set[Player] = players
        self.provinces: set[Province] = provinces
        self.units: set[Unit] = units
        self.unit_orders: dict[Unit, Order] = unit_orders
        self.build_orders: set[Order] = build_orders
        self.phase: Phase = phase

    def get_orders(self) -> set[Order]:
        return set(self.unit_orders.values()).union(self.build_orders)

    # TODO: (ALPHA) what if a player wants to change their build order? need to be able to remove build/disband orders
    def add_orders(self, orders: list[Order]):
        for order in orders:
            if isinstance(order, UnitOrder):
                self.unit_orders[order.unit] = order
            else:
                self.build_orders.add(order)
