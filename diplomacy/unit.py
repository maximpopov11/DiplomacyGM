from diplomacy.province import Province


class Unit:
    def __init__(self, province: Province):
        self.province = province


class Army(Unit):
    def __init__(self, province: Province):
        super().__init__(province)


class Fleet(Unit):
    def __init__(self, province: Province):
        super().__init__(province)
