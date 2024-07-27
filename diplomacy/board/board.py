from config import players
from diplomacy.player import Player


class Board:
    def __init__(self):
        # TODO: implement
        self.players = set()
        for name in players:
            self.players.add(Player(name))
        pass
