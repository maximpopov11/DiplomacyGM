from config import players
from diplomacy.player import Player


class Board:
    def __init__(self):
        # TODO: (1) implement (vector parse will build it in alpha)
        self.players = set()
        for name in players:
            self.players.add(Player(name))

        self.provinces = set()

        self.phase = None
