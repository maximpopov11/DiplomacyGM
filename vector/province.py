class Province:
    def __init__(self, coordinates):
        self.coordinates = coordinates
        self.name = None
        self.has_supply_center = False
        self.unit = None

    def set_name(self, name):
        self.name = name

    def set_has_supply_center(self, boolean):
        self.has_supply_center = boolean

    def set_unit(self, unit):
        self.unit = unit
