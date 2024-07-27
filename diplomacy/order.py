from typing import Optional

from diplomacy.player import Player
from diplomacy.province import Province
from diplomacy.unit import Army, Fleet, Unit


class Order:
    def __init__(self, unit: Unit):
        self.unit = unit


class Hold(Order):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Move(Order):
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination = destination


class Convoy(Order):
    def __init__(self, unit: Fleet, source: Army, destination: Province):
        super().__init__(unit)
        self.source = source
        self.destination = destination


class Support(Order):
    def __init__(self, unit: Unit, supporting: Order):
        super().__init__(unit)
        self.supporting = supporting


def parse(message: str, player_restriction: Optional[Player]) -> str:
    orders = str.splitlines(message)
    invalid = []
    for order in orders:
        try:
            _parse_order(order, player_restriction)
        except AssertionError:
            invalid.append(order)

    if invalid:
        response = 'The following orders were invalid:'
        for order in invalid:
            response += '\n' + order
    else:
        response = 'Orders validated successfully.'

    return response


hold = 'hold'
move = 'move'
support = 'support'
convoy = 'convoy'


order_dict = {
    hold: ['h', 'hold', 'holds'],
    move: ['-', '->', 'to', 'm', 'move', 'moves'],
    support: ['s', 'support', 'supports'],
    convoy: ['c', 'convoy', 'convoys'],
}


def _parse_order(order: str, player_restriction: Player) -> str:
    # TODO: (IMPL) implement parsing of individual order
    raise AssertionError('invalid')
