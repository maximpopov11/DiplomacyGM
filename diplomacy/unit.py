from diplomacy.player import Player
from diplomacy.province import Province


class Unit:
    def __init__(self, player: Player, province: Province):
        self.player = player
        self.province = province


class Army(Unit):
    def __init__(self, player: Player, province: Province):
        super().__init__(player, province)


class Fleet(Unit):
    def __init__(self, player: Player, province: Province):
        super().__init__(player, province)
