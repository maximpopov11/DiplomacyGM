from typing import Optional

from pydip.map.map import Map

from diplomacy.player import Player


# TODO: (MAP) island borders need to get colored in alongside the island fill
class Mapper:
    def __init__(self, board_map: Map):
        # TODO (MAP) new board_map state is given
        pass

    def get_moves_map(self, player_restriction: Optional[Player]) -> str:
        # TODO: (MAP) implement
        pass

    def get_results_map(self) -> str:
        # TODO: (MAP) implement
        pass
