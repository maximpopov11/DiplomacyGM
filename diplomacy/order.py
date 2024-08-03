from typing import List, Mapping, Optional

from diplomacy.persistence.adjudicator import Adjudicator
from diplomacy.player import Player
from diplomacy.province import Province
from diplomacy.unit import Army, Fleet, Unit


# TODO: (1) implement retreats (RetreatMoveCommand and RetreatDisbandCommand in library)
# TODO: (1) implement builds (AdjustmentCommandType.CREATE and DISBAND in library)
# TODO: (1) implement coring
class Order:
    def __init__(self, unit: Unit):
        self.unit = unit


class ComplexOrder(Order):
    """Complex orders are orders that operate on other orders (supports and convoys)."""
    def __init__(self, unit: Unit, source: Unit):
        super().__init__(unit)
        self.source = source


class Hold(Order):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Move(Order):
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination = destination


class ConvoyMove(Order):
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination = destination


class ConvoyTransport(ComplexOrder):
    def __init__(self, unit: Fleet, source: Army, destination: Province):
        super().__init__(unit, source)
        self.destination = destination


class Support(ComplexOrder):
    def __init__(self, unit: Unit, source: Unit, destination: Province):
        super().__init__(unit, source)
        self.destination = destination


def parse(
        message: str,
        player_restriction: Optional[Player],
        provinces: Mapping[str, Province],
        adjudicator: Adjudicator,
) -> str:
    orders = str.splitlines(message)
    valid = set()
    invalid = []
    for order in orders:
        try:
            valid.add(_parse_order(order, player_restriction, provinces))
        except AssertionError as error:
            invalid.append((order, error))

    adjudicator.add_orders(valid)

    if invalid:
        response = 'Some orders validated successfully. The following orders were invalid:'
        for order in invalid:
            response += f'\n{order[0]} with error: {order[1]}'
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


def _parse_order(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    if 'via' in order and 'convoy' in order:
        return _parse_convoy_move(order, player_restriction, provinces)

    for keyword in hold:
        if keyword in order:
            return _parse_hold(order, player_restriction, provinces)

    for keyword in move:
        if keyword in order:
            return _parse_move(order, player_restriction, provinces)

    for keyword in support:
        if keyword in order:
            return _parse_support(order, player_restriction, provinces)

    for keyword in convoy:
        if keyword in order:
            return _parse_convoy_transport(order, player_restriction, provinces)

    raise ValueError('Order does not contain any keywords:', order)


def _parse_convoy_move(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    position, destination = _parse_provinces(order, provinces, 2)
    if player_restriction is not None and position.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{position.name} which belongs to {position.unit.player}')
    return ConvoyMove(position.unit, destination)


def _parse_hold(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    province = _parse_provinces(order, provinces, 1)[0]
    if player_restriction is not None and province.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{province.name} which belongs to {province.unit.player}')
    return Hold(province.unit)


def _parse_move(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    position, destination = _parse_provinces(order, provinces, 2)
    if player_restriction is not None and position.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{position.name} which belongs to {position.unit.player}')
    return Move(position.unit, destination)


def _parse_convoy_transport(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    position, source, destination = _parse_provinces(order, provinces, 3)
    if player_restriction is not None and source.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{source.name} which belongs to {source.unit.player}')
    return ConvoyTransport(position.unit, source, destination)


def _parse_support(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    position, source, destination = _parse_provinces(order, provinces, 3)
    if player_restriction is not None and source.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{source.name} which belongs to {source.unit.player}')
    return Support(position.unit, source, destination)


def _parse_provinces(order: str, all_provinces: Mapping[str, Province], count: int) -> List[Province]:
    provinces = []
    for word in order:
        if word in all_provinces:
            provinces.append(all_provinces[word])
    if len(provinces) != count:
        raise ValueError(f'{count} provinces not found in order:', order)
    return provinces
