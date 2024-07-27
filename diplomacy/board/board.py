from config import players
from diplomacy.player import Player


class Board:
    def __init__(self):
        # TODO: (IMPL) implement
        self.players = set()
        for name in players:
            self.players.add(Player(name))

        self.provinces = set()

        self.phase = None
