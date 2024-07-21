from pydip.map.map import Map
from pydip.player.command.command import MoveCommand, ConvoyMoveCommand, ConvoyTransportCommand
from pydip.player.player import Player
from pydip.player.unit import UnitTypes
from pydip.turn.resolve import resolve_turn


game_master = 'GM'


def adjudicate(author: str) -> str:
    if author is not game_master:
        return author + ' is not authorized to adjudicate.'
    return _adjudicate()


def rollback(author: str) -> str:
    if author is not game_master:
        return author + ' is not authorized to rollback.'
    return _rollback()


def _adjudicate() -> str:
    territories = [
        {'name': 'Naples', 'coasts': ['Naples Coast']},
        {'name': 'Rome', 'coasts': ['Rome Coast']},
        {'name': 'Ionian Sea'},
    ]
    adjacencies = [
        ('Naples', 'Rome'),
        ('Naples', 'Ionian Sea'),
        ('Rome', 'Ionian Sea'),
    ]
    game_map = Map(territories, adjacencies)

    italy_units = [
        {'territory_name': 'Rome', 'unit_type': UnitTypes.TROOP},
        {'territory_name': 'Ionian Sea', 'unit_type': UnitTypes.FLEET},
    ]
    italy = Player("Italy", game_map, italy_units)
    turkey_units = [
        {'territory_name': 'Naples', 'unit_type': UnitTypes.TROOP},
    ]
    turkey = Player("Turkey", game_map, turkey_units)

    commands = [
        ConvoyMoveCommand(italy, italy.units[0], 'Naples'),
        ConvoyTransportCommand(italy, italy.units[1], italy.units[0], 'Naples'),
        MoveCommand(turkey, turkey.units[0], 'Rome'),
    ]

    new_unit_positions = resolve_turn(game_map, commands)

    print('Great success! (Actually something is off when convoys are involved, but without it it is good.)')

    return ''


def _rollback() -> str:
    return 'Pretend we rolled back the map to the last version!'
