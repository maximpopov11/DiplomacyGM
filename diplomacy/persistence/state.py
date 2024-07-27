from typing import Optional

from diplomacy.board.board import Board
from diplomacy.player import Player


class State:
    def __init__(self):
        # TODO: (IMPL) implement: state = board + orders
        # TODO: (IMPL) set all unset orders to hold (for pydip)
        self.board = Board()
        pass

    def get(self) -> Board:
        return self.board

    def get_player(self, name: str) -> Optional[Player]:
        for player in self.board.players:
            if player.name == name:
                return player
        return None


def get() -> State:
    # TODO: (IMPL) implement
    pass


def view(player_restriction: Optional[Player]) -> str:
    # TODO: (IMPL) implement
    return 'view current state (with orders drawn) not implemented yet'
