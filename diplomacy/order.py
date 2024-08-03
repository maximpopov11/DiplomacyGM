from typing import List, Mapping, Optional, Union

from diplomacy.persistence.adjudicator import Adjudicator
from diplomacy.phase import is_moves_phase, is_retreats_phase, is_adjustments_phase
from diplomacy.player import Player
from diplomacy.province import Province
from diplomacy.unit import Army, Fleet, Unit


class Order:
    def __init__(self):
        pass


class UnitOrder(Order):
    def __init__(self, unit: Unit):
        super().__init__()
        self.unit: Unit = unit


class ComplexOrder(UnitOrder):
    """Complex orders are orders that operate on other orders (supports and convoys)."""
    def __init__(self, unit: Unit, source: Unit):
        super().__init__(unit)
        self.source: Unit = source


class Hold(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Core(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Move(UnitOrder):
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination: Province = destination


class ConvoyMove(UnitOrder):
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination: Province = destination


class ConvoyTransport(ComplexOrder):
    def __init__(self, unit: Fleet, source: Army, destination: Province):
        super().__init__(unit, source)
        self.destination: Province = destination


class Support(ComplexOrder):
    def __init__(self, unit: Unit, source: Unit, destination: Province):
        super().__init__(unit, source)
        self.destination: Province = destination


class RetreatMove(UnitOrder):
    def __init__(self, unit: Unit, destination: Province):
        super().__init__(unit)
        self.destination: Province = destination


class RetreatDisband(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


class Build(Order):
    def __init__(self, province: Province, unit: Union[Army, Fleet]):
        super().__init__()
        self.province: Province = province
        self.unit: Union[Army, Fleet] = unit


class Disband(UnitOrder):
    def __init__(self, unit: Unit):
        super().__init__(unit)


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
            if is_moves_phase(adjudicator.phase):
                valid.add(_parse_order_moves(order, player_restriction, provinces))
            elif is_retreats_phase(adjudicator.phase):
                valid.add(_parse_order_retreats(order, player_restriction, provinces))
            elif is_adjustments_phase(adjudicator.phase):
                valid.add(_parse_order_adjustments(order, player_restriction, provinces))
            raise ValueError(f'Invalid phase: {adjudicator.phase}')
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
retreat_move = 'retreat move'
retreat_disband = 'retreat disband'
build = 'build'
disband = 'disband'
core = 'core'
army = 'army'
fleet = 'fleet'

order_dict = {
    hold: ['h', 'hold', 'holds'],
    move: ['-', '->', 'to', 'm', 'move', 'moves'],
    support: ['s', 'support', 'supports'],
    convoy: ['c', 'convoy', 'convoys'],
    core: ['core', 'cores'],

    retreat_move: ['-', '->', 'to', 'm', 'move', 'moves', 'r', 'retreat', 'retreats'],
    retreat_disband: ['d', 'disband', 'disbands', 'boom', 'explodes', 'dies'],

    build: ['b', 'build', 'place'],
    disband: ['d', 'disband', 'disbands', 'drop', 'drops', 'remove'],
    army: ['a', 'army', 'cannon'],
    fleet: ['f', 'fleet', 'boat', 'ship'],
}


def _parse_order_moves(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    order = order.lower()

    if 'via' in order and 'convoy' in order:
        return _parse_convoy_move(order, player_restriction, provinces)

    for keyword in hold:
        if keyword in order:
            return _parse_hold(order, player_restriction, provinces)

    for keyword in core:
        if keyword in order:
            return _parse_core(order, player_restriction, provinces)

    for keyword in move:
        if keyword in order:
            return _parse_move(order, player_restriction, provinces)

    for keyword in support:
        if keyword in order:
            return _parse_support(order, player_restriction, provinces)

    for keyword in convoy:
        if keyword in order:
            return _parse_convoy_transport(order, player_restriction, provinces)

    raise ValueError('Order does not contain any move phase keywords:', order)


def _parse_order_retreats(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    for keyword in retreat_move:
        if keyword in order:
            return _parse_retreat_move(order, player_restriction, provinces)

    for keyword in retreat_disband:
        if keyword in order:
            return _parse_retreat_disband(order, player_restriction, provinces)

    raise ValueError('Order does not contain any retreat phase keywords:', order)


def _parse_order_adjustments(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Order:
    for keyword in build:
        if keyword in order:
            return _parse_build(order, player_restriction, provinces)

    for keyword in disband:
        if keyword in order:
            return _parse_disband(order, player_restriction, provinces)

    raise ValueError('Order does not contain any adjustment phase keywords:', order)


def _parse_convoy_move(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> ConvoyMove:
    position, destination = _parse_provinces(order, provinces, 2)
    if player_restriction is not None and position.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{position.name} which belongs to {position.unit.player}')
    return ConvoyMove(position.unit, destination)


def _parse_hold(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Hold:
    province = _parse_provinces(order, provinces, 1)[0]
    if player_restriction is not None and province.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{province.name} which belongs to {province.unit.player}')
    return Hold(province.unit)


def _parse_core(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Core:
    province = _parse_provinces(order, provinces, 1)[0]
    if player_restriction is not None and province.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{province.name} which belongs to {province.unit.player}')
    return Core(province.unit)


def _parse_move(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Move:
    position, destination = _parse_provinces(order, provinces, 2)
    if player_restriction is not None and position.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{position.name} which belongs to {position.unit.player}')
    return Move(position.unit, destination)


def _parse_convoy_transport(
    order: str,
    player_restriction: Player,
    provinces: Mapping[str, Province]
) -> ConvoyTransport:
    position, source, destination = _parse_provinces(order, provinces, 3)
    if player_restriction is not None and source.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{source.name} which belongs to {source.unit.player}')
    return ConvoyTransport(position.unit, source, destination)


def _parse_support(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Support:
    position, source, destination = _parse_provinces(order, provinces, 3)
    if player_restriction is not None and source.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{source.name} which belongs to {source.unit.player}')
    return Support(position.unit, source, destination)


def _parse_retreat_move(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> RetreatMove:
    position, destination = _parse_provinces(order, provinces, 2)
    if player_restriction is not None and position.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{position.name} which belongs to {position.unit.player}')
    return RetreatMove(position.unit, destination)


def _parse_retreat_disband(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> RetreatDisband:
    province = _parse_provinces(order, provinces, 1)[0]
    if player_restriction is not None and province.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{province.name} which belongs to {province.unit.player}')
    return RetreatDisband(province.unit)


def _parse_build(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Build:
    province = _parse_provinces(order, provinces, 1)[0]
    if player_restriction is not None and province.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to build in '
                              f'{province.name} which belongs to {province.owner}')

    unit = None
    for word in order:
        if word in order_dict[army]:
            unit = Army
            break
        if word in order_dict[fleet]:
            unit = Fleet
            break
    if not unit:
        raise ValueError(f'Unit type could not be parsed in order: {order}')

    return Build(province, unit)


def _parse_disband(order: str, player_restriction: Player, provinces: Mapping[str, Province]) -> Disband:
    province = _parse_provinces(order, provinces, 1)[0]
    if player_restriction is not None and province.unit.player != player_restriction:
        raise PermissionError(f'You, {player_restriction.name}, do not have permissions to order the unit in '
                              f'{province.name} which belongs to {province.unit.player}')
    return Disband(province.unit)


def _parse_provinces(order: str, all_provinces: Mapping[str, Province], count: int) -> List[Province]:
    provinces = []
    for word in order:
        if word in {province.lower() for province in all_provinces}:
            provinces.append(all_provinces[word])
    if len(provinces) != count:
        raise ValueError(f'{count} provinces not found in order:', order)
    return provinces
