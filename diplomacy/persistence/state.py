from typing import Optional

from diplomacy.board.board import Board
from diplomacy.player import Player


# TODO: (FRAMEWORK) current board/orders state
# TODO: (FRAMEWORK) persist state: ideally in database, if easier can do file for now
# TODO: (FRAMEWORK) support multiple simultaneous games (can context see what server it is? else might need multiple bot instances)


class State:
    def __init__(self):
        # TODO: implement
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
    # TODO: implement
    return State()
    pass


def view(player_restriction: Optional[Player]) -> str:
    # TODO: implement
    return 'view current state (with orders drawn) not implemented yet'
