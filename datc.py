import unittest

from diplomacy.persistence.board import Board
from diplomacy.persistence.order import (
    Hold,
    Move,
    RetreatMove,
    ConvoyTransport,
    Support,
    Build,
    Disband,
)
from diplomacy.persistence.province import Location, Coast, Province, ProvinceType
from diplomacy.persistence.unit import UnitType, Unit
from diplomacy.persistence.player import Player
from diplomacy.persistence.phase import Phase
from diplomacy.adjudicator.adjudicator import MovesAdjudicator, RetreatsAdjudicator, BuildsAdjudicator, ResolutionState, Resolution

# These tests are based off https://webdiplomacy.net/doc/DATC_v3_0.html, with 
# https://github.com/diplomacy/diplomacy/blob/master/diplomacy/tests/test_datc.py being used as a reference as well.

# Allows for specifying units, uses the classic diplomacy board as that is used by DATC 
class BoardBuilder():
    def __init__(self, season: str = "Spring"):
        self.board = Board(
            players=set(),
            provinces=set(),
            units=set(),
            phase=Phase(f"{season} 1901", None, None),
            data=None,
            datafile=None
        )

        # here an illegal move is one that is caught and turned into a hold order, which includes supports and convoys 
        # which are missing the corresponding part
        # a failed move is one that is resolved by the adjudicator as failed, succeeded moved is similar
        self._listIllegal: list[Location] = []
        self._listNotIllegal: list[Location] = []
        self._listFail: list[Location] = []
        self._listSuccess: list[Location] = []
        self._listDislodge: list[Province] = []
        self._listNotDislodge: list[Province] = []
        self._listForcedDisband: list[Unit] = []
        self._listNotForcedDisband: list[Unit] = []

        self._listCreated: list[Province] = []
        self._listNotCreated: list[Province] = []

        self._listDisbanded: list[Province] = []
        self._listNotDisbanded: list[Province] = []

        self.build_count = None


        self.france = self._player("France")
        self.england = self._player("England")
        self.germany = self._player("Germany")
        self.italy = self._player("Italy")
        self.austria = self._player("Austria")
        self.russia = self._player("Russia")
        self.turkey = self._player("Turkey")

        self.initProvinces()

    # this initializes the connections and territories needed to run DATC's tests
    #  TODO Autogenerate this from a json file?
    def initProvinces(self):
        self.north_sea = self._sea("North Sea")
        self.picardy = self._land("Picardy")
        self.picardy_c = self._coast("m", self.picardy)
        self.liverpool = self._land("Liverpool")
        self.liverpool_c = self._coast("m", self.liverpool)
        self.irish_sea = self._sea("Irish Sea")
        self.kiel = self._land("Kiel", sc=True)
        self.kiel_c = self._coast("m", self.kiel)
        self.munich = self._land("Munich", sc=True)
        self.yorkshire = self._land("Yorkshire")
        self.yorkshire_c = self._coast("m", self.yorkshire)
        self.london = self._land("London")
        self.london_c = self._coast("m", self.london)
        self.wales = self._land("Wales")
        self.wales_c = self._coast("m", self.wales)
        self.belgium = self._land("Belgium")
        self.belgium_c = self._coast("m", self.belgium)
        self.venice = self._land("Venice")
        self.venice_c = self._coast("m", self.venice)
        self.trieste = self._land("Trieste")
        self.trieste_c = self._coast("m", self.trieste)
        self.tyrolia = self._land("Tyrolia")
        self.rome = self._land("Rome")
        self.rome_c = self._coast("m", self.rome)
        self.adriatic_sea = self._sea("Adriatic Sea")
        self.tyrrhenian_sea = self._sea("Tyrrhenian Sea")
        self.apulia = self._land("Apulia")
        self.apulia_c = self._coast("m", self.apulia)
        self.vienna = self._land("Vienna")
        self.gascony = self._land("Gascony")
        self.gascony_c = self._coast("m", self.gascony)
        self.spain = self._land("Spain")
        self.spain_nc = self._coast("nc", self.spain)
        self.spain_sc = self._coast("sc", self.spain)
        self.mid_atlantic_ocean = self._sea("Mid-Atlantic Ocean")
        self.gulf_of_bothnia = self._sea("Gulf of Bothnia")
        self.barents_sea = self._sea("Barents Sea")
        self.st_petersburg = self._land("St. Petersburg")
        self.st_petersburg_nc = self._coast("nc", self.st_petersburg)
        self.st_petersburg_sc = self._coast("sc", self.st_petersburg)
        self.marseilles = self._land("Marseilles")
        self.marseilles_c = self._coast("m", self.marseilles)
        self.western_mediterranean = self._sea("Western Mediteranean")
        self.eastern_mediterranean = self._sea("Eastern Mediteranean")
        self.gulf_of_lyon = self._sea("Gulf of Lyon")
        self.north_atlantic_ocean = self._sea("North Atlantic Ocean")
        self.bulgaria = self._land("Bulgaria")
        self.bulgaria_ec = self._coast("nc", self.bulgaria)
        self.bulgaria_sc = self._coast("sc", self.bulgaria)
        self.aegean_sea = self._sea("Aegean Sea")
        self.black_sea = self._sea("Black Sea")
        self.constantinople = self._land("Constantinople")
        self.constantinople_c = self._coast("m", self.constantinople)
        self.ankara = self._land("Ankara")
        self.ankara_c = self._coast("m", self.ankara)
        self.smyrna = self._land("Smyrna")
        self.serbia = self._land("Serbia")
        self.ionian_sea = self._sea("Ionian Sea")
        self.naples = self._land("Naples")
        self.naples_c = self._coast("m", self.naples)
        self.tunis = self._land("Tunis")
        self.tunis_c = self._coast("m", self.tunis)
        self.english_channel = self._sea("English Channel")
        self.burgundy = self._land("Burgundy")
        self.berlin = self._land("Berlin")
        self.berlin_c = self._coast("m", self.berlin)
        self.prussia = self._land("Prussia")
        self.prussia_c = self._coast("m", self.prussia)
        self.baltic_sea = self._sea("Baltic Sea")
        self.silesia = self._land("Silesia")
        self.sweden = self._land("Sweden")
        self.sweden_c = self._coast("m", self.sweden)
        self.livonia = self._land("Livonia")
        self.livonia_c = self._coast("m", self.livonia)
        self.finland = self._land("Finland")
        self.finland_c = self._coast("m", self.finland)
        self.greece = self._land("Greece")
        self.greece_c = self._coast("m", self.greece)
        self.albania = self._land("Albania")
        self.albania_c = self._coast("m", self.albania)
        self.warsaw = self._land("Warsaw", sc=True)
        self.armenia = self._land("Armenia")
        self.denmark = self._land("Denmark")
        self.denmark_c = self._coast("m", self.denmark)
        self.rumania = self._land("Rumania")
        self.rumania_c = self._coast("m", self.rumania)
        self.budapest = self._land("Budapest")
        self.holland = self._land("Holland")
        self.holland_c = self._coast("m", self.holland)
        self.edinburgh = self._land("Edinburgh")
        self.edinburgh_c = self._coast("m", self.edinburgh)
        self.galicia = self._land("Galicia")
        self.ruhr = self._land("Ruhr")
        self.norwegian_sea = self._sea("Norwegian Sea")
        self.helgoland_bight = self._sea("Helgoland Bight")
        self.skagerrak = self._sea("Skagerrak")
        self.norway = self._land("Norway")
        self.norway_c = self._coast("m", self.norway)
        self.portugal = self._land("Portugal")
        self.portugal_c = self._coast("m", self.portugal)
        self.sevastopol = self._land("Sevastopol")
        self.brest = self._land("Brest")
        self.brest_c = self._coast("m", self.brest)
        self.paris = self._land("Paris")
        self.north_africa = self._land("North Africa")
        self.clyde = self._land("Clyde")
        self.clyde_c = self._coast("m", self.clyde)
        self.bohemia = self._land("Bohemia")
        self.moscow = self._land("Moscow", sc=True)

        self.liverpool.adjacent = set([self.irish_sea, self.yorkshire, self.wales, self.edinburgh, self.north_atlantic_ocean, self.clyde])
        self.liverpool_c.adjacent_seas = set([self.irish_sea, self.north_atlantic_ocean])
        self.irish_sea.adjacent = set([self.liverpool, self.mid_atlantic_ocean, self.north_atlantic_ocean, self.english_channel])
        self.mid_atlantic_ocean.adjacent = set([self.irish_sea, self.spain, self.western_mediterranean, self.gascony, self.portugal, self.english_channel, self.brest, self.north_africa, self.north_atlantic_ocean])
        self.north_sea.adjacent = set([self.yorkshire, self.edinburgh, self.belgium, self.london, self.english_channel, self.norway, self.denmark, self.holland, self.skagerrak])
        self.yorkshire.adjacent = set([self.north_sea, self.liverpool, self.wales, self.london, self.edinburgh])
        self.yorkshire_c.adjacent_seas = set([self.north_sea])
        self.london.adjacent = set([self.yorkshire, self.north_sea, self.wales, self.english_channel, self.edinburgh])
        self.london_c.adjacent_seas = set([self.north_sea, self.english_channel])
        self.edinburgh.adjacent = set([self.liverpool, self.yorkshire, self.clyde, self.north_sea, self.norwegian_sea])
        self.edinburgh_c.adjacent_seas = set([self.north_sea])
        self.english_channel.adjacent = set([self.picardy, self.london, self.belgium, self.north_sea, self.picardy, self.brest, self.wales, self.irish_sea])
        self.wales.adjacent = set([self.london, self.liverpool, self.yorkshire, self.english_channel, self.irish_sea])
        self.wales_c.adjacent_seas = set([self.english_channel, self.irish_sea])
        self.north_atlantic_ocean.adjacent = set([self.irish_sea, self.mid_atlantic_ocean, self.clyde, self.norwegian_sea, self.liverpool])
        self.norwegian_sea.adjacent = set([self.edinburgh, self.north_sea, self.north_atlantic_ocean, self.clyde, self.norway])
        self.clyde.adjacent = set([self.north_atlantic_ocean, self.norwegian_sea, self.edinburgh, self.liverpool])
        self.clyde_c.adjacent_seas = set([self.north_atlantic_ocean, self.norwegian_sea])

        self.north_africa.adjacent = set([self.mid_atlantic_ocean, self.western_mediterranean, self.tunis])

        self.picardy.adjacent = set([self.belgium, self.english_channel, self.burgundy, self.paris, self.brest])
        self.picardy_c.adjacent_seas = set([self.english_channel])

        self.kiel.adjacent = set([self.munich, self.berlin, self.baltic_sea, self.holland, self.helgoland_bight])
        self.kiel_c.adjacent_seas = set([self.baltic_sea, self.helgoland_bight])
        self.munich.adjacent = set([self.kiel, self.tyrolia, self.silesia, self.berlin, self.bohemia, self.burgundy])
        self.berlin.adjacent = set([self.kiel, self.prussia, self.baltic_sea, self.silesia, self.munich])
        self.berlin_c.adjacent_seas=set([self.baltic_sea])
        self.prussia.adjacent = set([self.berlin, self.baltic_sea, self.silesia, self.livonia, self.warsaw])
        self.prussia_c.adjacent_seas = set([self.baltic_sea])
        self.baltic_sea.adjacent = set([self.berlin, self.prussia, self.gulf_of_bothnia, self.sweden, self.livonia])
        self.silesia.adjacent = set([self.berlin, self.prussia, self.munich, self.bohemia])
        self.bohemia.adjacent = set([self.munich, self.tyrolia, self.venice, self.silesia])

        self.sweden.adjacent = set([self.gulf_of_bothnia, self.baltic_sea, self.finland, self.norway, self.skagerrak])
        self.sweden_c.adjacent_seas = set([self.baltic_sea, self.gulf_of_bothnia, self.skagerrak])
        self.finland.adjacent = set([self.sweden, self.st_petersburg, self.gulf_of_bothnia, self.norway])
        self.finland_c.adjacent_seas = set([self.gulf_of_bothnia])
        self.denmark.adjacent = set([self.baltic_sea, self.sweden, self.kiel])
        self.denmark_c.adjacent_seas = set([self.baltic_sea, self.north_sea, self.helgoland_bight])
        self.norway.adjacent = set([self.north_sea, self.skagerrak, self.norwegian_sea, self.sweden, self.barents_sea])
        self.norway_c.adjacent_seas = set([self.north_sea, self.skagerrak, self.norwegian_sea, self.barents_sea])

        self.belgium.adjacent = set([self.north_sea, self.english_channel, self.picardy, self.burgundy, self.holland, self.north_sea])
        self.belgium_c.adjacent_seas = set([self.north_sea, self.english_channel])
        self.holland.adjacent = set([self.north_sea, self.belgium, self.kiel, self.ruhr])
        self.holland_c.adjacent_seas = set([self.north_sea, self.helgoland_bight])
        self.helgoland_bight.adjacent = set([self.kiel, self.holland, self.north_sea, self.denmark])
        self.skagerrak.adjacent = set([self.north_sea, self.sweden, self.denmark, self.norway])
        self.ruhr.adjacent = set([self.belgium, self.holland, self.kiel])

        self.venice.adjacent = set([self.trieste, self.tyrolia, self.rome, self.apulia])
        self.trieste.adjacent = set([self.vienna, self.venice, self.tyrolia, self.serbia, self.adriatic_sea, self.albania])
        self.trieste_c.adjacent_seas = set([self.adriatic_sea])
        self.tyrolia.adjacent = set([self.trieste, self.venice, self.vienna, self.munich])
        self.vienna.adjacent = set([self.tyrolia, self.trieste, self.galicia, self.budapest, self.bohemia])
        self.rome.adjacent = set([self.venice, self.apulia, self.tyrrhenian_sea])
        self.apulia.adjacent = set([self.rome, self.venice, self.ionian_sea, self.adriatic_sea])
        self.apulia_c.adjacent_seas = set([self.ionian_sea, self.adriatic_sea])
        self.naples.adjacent = set([self.tyrrhenian_sea, self.rome, self.apulia, self.ionian_sea])
        self.tunis.adjacent = set([self.tyrrhenian_sea, self.western_mediterranean, self.ionian_sea])

        self.greece.adjacent = set([self.serbia, self.bulgaria, self.aegean_sea, self.adriatic_sea, self.ionian_sea, self.albania])
        self.greece_c.adjacent_seas = set([self.aegean_sea, self.adriatic_sea, self.ionian_sea])
        self.albania.adjacent = set([self.greece, self.adriatic_sea, self.serbia, self.ionian_sea, self.trieste])
        self.albania_c.adjacent_seas = set([self.adriatic_sea, self.ionian_sea])

        self.rome_c.adjacent_seas = set([self.tyrrhenian_sea])
        self.venice_c.adjacent_seas = set([self.adriatic_sea])
        self.naples_c.adjacent_seas = set([self.tyrrhenian_sea, self.ionian_sea])
        self.tunis_c.adjacent_seas = set([self.tyrrhenian_sea, self.western_mediterranean, self.ionian_sea])

        self.spain.adjacent = set([self.gascony, self.western_mediterranean, self.mid_atlantic_ocean, self.gulf_of_lyon, self.portugal])
        self.gascony.adjacent = set([self.spain, self.marseilles, self.burgundy, self.mid_atlantic_ocean])
        self.burgundy.adjacent = set([self.gascony, self.marseilles, self.belgium, self.munich])
        self.western_mediterranean.adjacent = set([self.mid_atlantic_ocean, self.spain, self.gulf_of_lyon, self.tunis])
        self.marseilles.adjacent = set([self.gascony, self.spain, self.gulf_of_lyon, self.belgium, self.burgundy])
        self.gulf_of_lyon.adjacent = set([self.spain, self.western_mediterranean, self.marseilles])
        self.brest.adjacent = set([self.picardy, self.english_channel, self.paris, self.mid_atlantic_ocean])
        self.brest_c.adjacent_seas = set([self.picardy, self.english_channel, self.paris, self.mid_atlantic_ocean])
        self.paris.adjacent = set([self.brest, self.picardy])

        self.spain_nc.adjacent_seas = set([self.mid_atlantic_ocean])
        self.spain_sc.adjacent_seas = set([self.mid_atlantic_ocean, self.western_mediterranean, self.gulf_of_lyon])
        self.gascony_c.adjacent_seas = set([self.mid_atlantic_ocean])
        self.portugal.adjacent = set([self.mid_atlantic_ocean, self.spain])
        self.portugal_c.adjacent_seas = set([self.mid_atlantic_ocean])
        self.marseilles_c.adjacent_seas = set([self.gulf_of_lyon])

        self.gulf_of_bothnia.adjacent = set([self.st_petersburg, self.baltic_sea, self.sweden, self.livonia])
        self.livonia.adjacent = set([self.gulf_of_bothnia, self.baltic_sea, self.prussia])
        self.livonia_c.adjacent_seas = set([self.gulf_of_bothnia, self.baltic_sea])
        self.barents_sea.adjacent = set([self.st_petersburg, self.russia, self.norwegian_sea, self.norway])
        self.st_petersburg.adjacent = set([self.gulf_of_bothnia, self.barents_sea])
        self.st_petersburg_nc.adjacent_seas = set([self.barents_sea])
        self.st_petersburg_sc.adjacent_seas = set([self.gulf_of_bothnia])
        self.warsaw.adjacent = set([self.prussia])

        self.bulgaria.adjacent = set([self.aegean_sea, self.black_sea, self.constantinople, self.serbia, self.greece, self.rumania])
        self.bulgaria_ec.adjacent_seas = set([self.black_sea])
        self.bulgaria_sc.adjacent_seas = set([self.aegean_sea])
        self.serbia.adjacent = set([self.bulgaria, self.trieste, self.greece, self.budapest])

        self.tyrrhenian_sea.adjacent = set([self.rome, self.western_mediterranean, self.ionian_sea, self.tunis, self.gulf_of_lyon, self.naples, self.apulia])
        self.aegean_sea.adjacent = set([self.bulgaria, self.constantinople, self.smyrna, self.ionian_sea, self.greece])
        self.black_sea.adjacent = set([self.bulgaria, self.constantinople, self.ankara, self.rumania])
        self.ionian_sea.adjacent = set([self.naples, self.tyrrhenian_sea, self.apulia, self.adriatic_sea, self.aegean_sea, self.tunis, self.greece, self.eastern_mediterranean, self.rome])
        self.adriatic_sea.adjacent = set([self.trieste, self.ionian_sea, self.apulia, self.venice, self.greece])
        self.constantinople.adjacent = set([self.ankara, self.smyrna, self.aegean_sea, self.black_sea, self.bulgaria])
        self.constantinople_c.adjacent_seas = set([self.aegean_sea, self.black_sea])
        self.ankara.adjacent = set([self.constantinople, self.smyrna, self.black_sea, self.armenia])
        self.ankara_c.adjacent_seas = set([self.black_sea])
        self.smyrna.adjacent = set([self.constantinople, self.ankara, self.black_sea, self.armenia])
        self.eastern_mediterranean.adjacent = set([self.smyrna, self.aegean_sea, self.ionian_sea])
        self.armenia.adjacent = set([self.ankara, self.smyrna])
        self.rumania.adjacent = set([self.black_sea, self.bulgaria, self.budapest])
        self.budapest.adjacent = set([self.rumania, self.galicia, self.vienna, self.trieste])
        self.galicia.adjacent = set([self.vienna, self.budapest])
        self.rumania_c.adjacent_seas = set([self.black_sea])

    def _player(self, name):
        player = Player(
            name=name,
            color="",
            vscc = 0,
            iscc = 0,
            centers = set(),
            units=set()
        )

        self.board.players.add(player)
        return player
    
    def _land(self, name: str, sc=False):
        return self._province(name, ProvinceType.LAND, sc)

    def _sea(self, name: str, sc=False):
        return self._province(name, ProvinceType.SEA, sc)

    def _province(self, name: str, type: ProvinceType, sc):
        province = Province(
            name=name,
            coordinates=None,
            primary_unit_coordinate=(0,0),
            retreat_unit_coordinate=(0,0),
            province_type=type,
            has_supply_center=sc,
            adjacent=set(),
            coasts=set(),
            core=None,
            owner=None,
            local_unit=None,
        )

        self.board.provinces.add(province)

        return province
    
    def _coast(self, suffix: str, P: Province):
        assert P.type == ProvinceType.LAND
    
        coast = Coast(
            name=f"{P.name}({suffix})",
            primary_unit_coordinate=None,
            retreat_unit_coordinate=None,
            adjacent_seas=set(),
            province=P
        )

        P.coasts.add(coast)

        return coast

    def army(self, land: Province, player: Player) -> Unit:
        assert land.type == ProvinceType.LAND or ProvinceType.ISLAND

        unit = Unit(
            UnitType.ARMY,
            player,
            land,
            None,
            None
        )

        unit.player = player
        land.unit = unit

        player.units.add(unit)
        self.board.units.add(unit)

        return unit
    
    def inject_centers(self, player: Player, c: int):
        player.centers = set([self._land(f"{player.name}{c}", sc=True) for i in range(c)])
    
    def fleet(self, loc: Coast | Province, player: Player):
        if (isinstance(loc, Province)):
            assert loc.type == ProvinceType.SEA or loc.type == ProvinceType.ISLAND

            unit = Unit(
                UnitType.FLEET,
                player,
                loc,
                None,
                None
            )

            loc.unit = unit
        else:
            unit = Unit(
                UnitType.FLEET,
                player,
                loc.province,
                loc,
                None
            )

            loc.province.unit = unit

        player.units.add(unit)
        self.board.units.add(unit)

        return unit

    def move(self, player: Player, type: UnitType, place: Location, to: Location) -> Unit:
        if (type == UnitType.FLEET):
            unit = self.fleet(place, player)
        else:
            unit = self.army(place, player)

        order = Move(to)
        unit.order = order

        return unit

    def convoy(self, player: Player, place: Location, source: Unit, to: Location) -> Unit:
        unit = self.fleet(place, player)
        
        order = ConvoyTransport(source, to)
        unit.order = order

        return unit
    
    def supportMove(self, player: Player, type: UnitType, place: Location, source: Unit, to: Location) -> Unit:
        if (type == UnitType.FLEET):
            unit = self.fleet(place, player)
        else:
            unit = self.army(place, player)

        order = Support(source, to)
        unit.order = order

        return unit

    def hold(self, player: Player, type: UnitType, place: Location) -> Unit:
        if (type == UnitType.FLEET):
            unit = self.fleet(place, player)
        else:
            unit = self.army(place, player)

        order = Hold()
        unit.order = order

        return unit

    def supportHold(self, player: Player, type: UnitType, place: Location, source: Unit) -> Unit:
        if (type == UnitType.FLEET):
            unit = self.fleet(place, player)
        else:
            unit = self.army(place, player)

        order = Support(source, source.location())
        unit.order = order

        return unit
    
    def retreat(self, unit: Unit, place: Location):
        unit.order = RetreatMove(place)
        pass

    def build(self, player: Player, *places: tuple[UnitType, Location]):
        player.build_orders |= set([Build(info[1], info[0]) for info in places])

    def disband(self, player: Player, *places: Location):
        player.build_orders |= set([Disband(place) for place in places])

    def core(self, player: Player, *places: Province):
        for place in places:
            place.owner = player
            place.core = player

    def assertIllegal(self, *units: Unit):
        for unit in units:
            loc = unit.location()
            if (isinstance(loc, Coast)):
                loc = loc.province
            self._listIllegal.append(loc)

    def assertNotIllegal(self, *units: Unit):
        for unit in units:
            loc = unit.location()
            if (isinstance(loc, Coast)):
                loc = loc.province
            self._listNotIllegal.append(loc)

    def assertFail(self, *units: Unit):
        for unit in units:
            loc = unit.location()
            if (isinstance(loc, Coast)):
                loc = loc.province
            self._listFail.append(loc)

    def assertSuccess(self, *units: Unit):
        for unit in units:
            loc = unit.location()
            if (isinstance(loc, Coast)):
                loc = loc.province
            self._listSuccess.append(loc)

    def assertDislodge(self, *units: Unit):
        for unit in units:
            loc = unit.location()
            if (isinstance(loc, Coast)):
                loc = loc.province
            self._listDislodge.append(loc)

    def assertNotDislodge(self, *units: Unit):
        for unit in units:
            loc = unit.location()
            if (isinstance(loc, Coast)):
                loc = loc.province
            self._listNotDislodge.append(loc)

    # used for retreat testing
    def assertForcedDisband(self, *units: Unit):
        for unit in units:
            self._listForcedDisband.append(unit)

    def assertNotForcedDisband(self, *units: Unit):
        for unit in units:
            self._listNotForcedDisband.append(unit)

    # used for retreat testing
    def assertCreated(self, *provinces: Province):
        for province in provinces:
            self._listCreated.append(province)

    def assertNotCreated(self, *provinces: Province):
        for province in provinces:
            self._listNotCreated.append(province)

    def assertDisbanded(self, *provinces: Province):
        for province in provinces:
            self._listDisbanded.append(province)

    def assertNotDisbanded(self, *provinces: Province):
        for province in provinces:
            self._listNotDisbanded.append(province)

    def assertBuildCount(self, count: int):
        self.build_count = count

    # used when testing the move phases of things
    def moves_adjudicate(self, test: unittest.TestCase):
        adj = MovesAdjudicator(board=self.board)
        
        for order in adj.orders:
            order.state = ResolutionState.UNRESOLVED

        for order in adj.orders:
            adj._resolve_order(order)

        for order in adj.orders:
            print(order)

        illegal_units = []
        succeeded_units = []
        failed_units = []

        for illegal_order in adj.failed_or_invalid_units:
            loc = illegal_order.location
            if (isinstance(loc, Coast)):
                illegal_units.append(loc.province)
            elif (isinstance(loc, Province)):
                illegal_units.append(loc)
            else:
                assert False % "Unknown illegal location type"

        for order in adj.orders:
            if (order.resolution == Resolution.SUCCEEDS):
                succeeded_units.append(order.current_province)
            else:
                failed_units.append(order.current_province)

        for illegal in self._listIllegal:
            test.assertTrue(illegal in illegal_units, f"Move by {illegal.name} expected to be illegal")
        for notillegal in self._listNotIllegal:
            test.assertTrue(notillegal not in illegal_units, f"Move by {notillegal.name} expected not to be illegal")

        for fail in self._listFail:
            test.assertTrue(fail in failed_units, f"Move by {fail.name} expected to fail")
        for succeed in self._listSuccess:
            test.assertTrue(succeed in succeeded_units, f"Move by {succeed.name} expected to succeed")

        adj._update_board()

        for dislodge in self._listDislodge:
            test.assertTrue(dislodge.dislodged_unit != None, f"Expected dislodged unit in {dislodge.name}")
        for notdislodge in self._listNotDislodge:
            test.assertTrue(notdislodge.dislodged_unit == None, f"Expected no dislodged unit in {notdislodge.name}")


        return adj
    
    def retreats_adjudicate(self, test: unittest.TestCase):
        adj = RetreatsAdjudicator(board=self.board)
        adj.run()
        for disband in self._listForcedDisband:
            test.assertTrue(disband not in disband.player.units, f"Expected unit {disband} to be removed")
        for notDisband in self._listNotForcedDisband:
            test.assertTrue(notDisband in notDisband.player.units, f"Expected unit {notDisband} to not be removed")

    def builds_adjudicate(self, test: unittest.TestCase):
        current_units = self.board.units.copy()
        
        adj = BuildsAdjudicator(board=self.board)
        adj.run()

        # print(current_units)
        # print(self.board.units)

        created_units = self.board.units - current_units
        created_provinces = map(lambda x: x.province, created_units)
        removed_units = current_units - self.board.units
        removed_provinces = map(lambda x: x.province, removed_units)
        
        for create in self._listCreated:
            test.assertTrue(create in created_provinces, f"Expected province {create} to have unit created")
        for notCreated in self._listNotCreated:
            test.assertTrue(notCreated not in created_provinces, f"Expected province {notCreated} to not have unit created")

        for disband in self._listDisbanded:
            test.assertTrue(disband in removed_provinces, f"Expected province {disband} to have unit removed")
        for notDisband in self._listNotDisbanded:
            test.assertTrue(notDisband not in removed_provinces, f"Expected province {notDisband} to not have unit removed")

        test.assertTrue(self.build_count == None or (len(self.board.units) - len(current_units)) == self.build_count, f"Expected {self.build_count} builds")

class TestDATC(unittest.TestCase):

    def test_6_a_1(self):
        """ 6.A.1 TEST CASE, MOVING TO AN AREA THAT IS NOT A NEIGHBOUR
            Check if an illegal move (without convoy) will fail.
            England: F North Sea - Picardy
            Order should fail.
        """
        b = BoardBuilder()
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.picardy)

        b.assertIllegal(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_a_2(self):
        """ 6.A.2. TEST CASE, MOVE ARMY TO SEA
            Check if an army could not be moved to open sea.
            England: A Liverpool - Irish Sea
            Order should fail.
        """
        b = BoardBuilder()
        f_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.irish_sea)

        b.assertIllegal(f_liverpool)
        b.moves_adjudicate(self)

    def test_6_a_3(self):
        """ 6.A.3. TEST CASE, MOVE FLEET TO LAND
            Check whether a fleet can not move to land.
            Germany: F Kiel - Munich
            Order should fail.
        """
        b = BoardBuilder()
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.munich)
        b.assertIllegal(f_kiel)
        b.moves_adjudicate(self)

    def test_6_a_4(self):
        """ 6.A.4. TEST CASE, MOVE TO OWN SECTOR
            Moving to the same sector is an illegal move (2000 rulebook, page 4,
            "An Army can be ordered to move into an adjacent inland or coastal province.").
            Germany: F Kiel - Kiel
            Program should not crash.
        """
        b = BoardBuilder()
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.kiel_c)

        b.assertIllegal(f_kiel)
        b.moves_adjudicate(self)

    # DEVIATES
    def test_6_a_5_fail(self):
        """ 6.A.5. TEST CASE, MOVE TO OWN SECTOR WITH CONVOY
            Moving to the same sector is still illegal with convoy (2000 rulebook, page 4,
            "Note: An Army can move across water provinces from one coastal province to another...").
            England: F North Sea Convoys A Yorkshire - Yorkshire
            England: A Yorkshire - Yorkshire
            England: A Liverpool Supports A Yorkshire - Yorkshire
            Germany: F London - Yorkshire
            Germany: A Wales Supports F London - Yorkshire
            The move of the army in Yorkshire is illegal. This makes the support of Liverpool also illegal and without
            the support, the Germans have a stronger force. The army in London dislodges the army in Yorkshire.
        """
        b = BoardBuilder()
        a_yorkshire = b.move(b.england, UnitType.ARMY, b.yorkshire, b.yorkshire)
        f_north_sea = b.convoy(b.england, b.north_sea, a_yorkshire, b.yorkshire)
        a_liverpool = b.supportMove(b.england, UnitType.ARMY, b.liverpool, a_yorkshire, b.yorkshire)
        f_london = b.move(b.germany, UnitType.FLEET, b.london_c, b.yorkshire_c);
        a_wales = b.supportMove(b.germany, UnitType.ARMY, b.wales, f_london, b.yorkshire)

        b.assertIllegal(a_yorkshire, f_north_sea)
        # since the bot considers support holds as support moves in place, the england support move 
        # really becomes a support hold, so we expected the london move to fail -- contrary to 
        # what DATC expects; this test expects this to deviate
        b.assertFail(f_london)
        b.assertSuccess(a_liverpool)
        b.moves_adjudicate(self)

    # NOT APPLICABLE 6_a_6; TEST CASE, ORDERING A UNIT OF ANOTHER COUNTRY

    def test_6_a_7(self):
        """ 6.A.7. TEST CASE, ONLY ARMIES CAN BE CONVOYED
            A fleet can not be convoyed.
            England: F London - Belgium
            England: F North Sea Convoys A London - Belgium
            Move from London to Belgium should fail.
        """
        b = BoardBuilder()
        f_london = b.move(b.england, UnitType.FLEET, b.london_c, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, f_london, b.belgium)
        
        b.assertIllegal(f_london, f_north_sea)
        b.moves_adjudicate(self)

    def test_6_a_8(self):
        """ 6.A.8. TEST CASE, SUPPORT TO HOLD YOURSELF IS NOT POSSIBLE
            An army can not get an additional hold power by supporting itself.
            Italy: A Venice - Trieste
            Italy: A Tyrolia Supports A Venice - Trieste
            Austria: F Trieste Supports F Trieste
            The army in Trieste should be dislodged.
        """
        b = BoardBuilder()
        a_venice = b.move(b.italy, UnitType.ARMY, b.venice, b.trieste)
        a_tyrolia = b.supportMove(b.italy, UnitType.ARMY, b.tyrolia, a_venice, b.trieste)
        f_trieste = b.fleet(b.trieste_c, b.austria)
        order = Support(f_trieste, b.trieste_c)
        f_trieste.order = order

        b.assertDislodge(f_trieste)
        b.moves_adjudicate(self)

    def test_6_a_9(self):
        """ 6.A.9. TEST CASE, FLEETS MUST FOLLOW COAST IF NOT ON SEA
            If two places are adjacent, that does not mean that a fleet can move between
            those two places. An implementation that only holds one list of adj. places for each place, is incorrect
            Italy: F Rome - Venice
            Move fails. An army can go from Rome to Venice, but a fleet can not.
        """
        b = BoardBuilder()
        f_rome = b.move(b.italy, UnitType.FLEET, b.rome_c, b.venice_c)
        
        b.assertIllegal(f_rome)
        b.moves_adjudicate(self)

    def test_6_a_10(self):
        """ 6.A.10. TEST CASE, SUPPORT ON UNREACHABLE DESTINATION NOT POSSIBLE
            The destination of the move that is supported must be reachable by the supporting unit.
            Austria: A Venice Hold
            Italy: F Rome Supports A Apulia - Venice
            Italy: A Apulia - Venice
            The support of Rome is illegal, because Venice can not be reached from Rome by a fleet.
            Venice is not dislodged.
        """
        b = BoardBuilder()
        a_venice = b.hold(b.austria, UnitType.ARMY, b.venice)
        a_apulia = b.move(b.austria, UnitType.ARMY, b.apulia, b.venice)
        f_rome = b.supportMove(b.italy, UnitType.FLEET, b.rome_c, a_apulia, b.venice)

        b.assertIllegal(f_rome)
        b.assertFail(a_apulia)
        b.assertNotDislodge(a_venice)
        b.moves_adjudicate(self)

    def test_6_a_11(self):
        """ 6.A.11. TEST CASE, SIMPLE BOUNCE
            Two armies bouncing on each other.
            Austria: A Vienna - Tyrolia
            Italy: A Venice - Tyrolia
            The two units bounce.
        """
        b = BoardBuilder()
        a_vienna = b.move(b.austria, UnitType.ARMY, b.vienna, b.tyrolia)
        a_venice = b.move(b.italy, UnitType.ARMY, b.venice, b.tyrolia)

        b.assertFail(a_vienna)
        b.assertFail(a_venice)
        b.moves_adjudicate(self)

    def test_6_a_12(self):
        """ 6.A.12. TEST CASE, BOUNCE OF THREE UNITS
            If three units move to the same place, the adjudicator should not bounce
            the first two units and then let the third unit go to the now open place.
            Austria: A Vienna - Tyrolia
            Germany: A Munich - Tyrolia
            Italy: A Venice - Tyrolia
            The three units bounce.
        """
        b = BoardBuilder()
        a_vienna = b.move(b.austria, UnitType.ARMY, b.vienna, b.tyrolia)
        a_venice = b.move(b.italy, UnitType.ARMY, b.venice, b.tyrolia)
        a_munich = b.move(b.germany, UnitType.ARMY, b.munich, b.tyrolia)

        b.assertFail(a_vienna)
        b.assertFail(a_venice)
        b.assertFail(a_munich)
        b.moves_adjudicate(self)

    # NOT APPLICABLE 6_b_1; MOVING WITH UNSPECIFIED COAST WHEN COAST IS NECESSARY

    # NOT APPLICABLE 6_b_2; TEST CASE, MOVING WITH UNSPECIFIED COAST WHEN COAST IS NOT NECESSARY

    def test_6_b_3_fail(self):
        """ 6.B.3. TEST CASE, MOVING WITH WRONG COAST WHEN COAST IS NOT NECESSARY
            If only one coast is possible, but the wrong coast can be specified.
            France: F Gascony - Spain(sc)
            If the rules are played very clemently, a move will be attempted to the north coast of Spain.
            However, since this order is very clear and precise, it is more common that the move fails (see 4.B.3).
            I prefer that the move fails.
        """
        b = BoardBuilder()
        f_gascony = b.move(b.france, UnitType.FLEET, b.gascony_c, b.spain_sc)

        b.assertSuccess(f_gascony) # this should really be a fail but the current code doesn't check this properly
        b.moves_adjudicate(self)

    # this test is written to work with the current `get_adjacent_coasts` which has 
    # false positives
    def test_6_b_3_variant(self):
        """ Variant of 6.B.3 which works correctly under current get_adjacent_coasts,
        Russia: F Gulf of Bothnia - St Petersburg(nc)
        should fail
        """
        b = BoardBuilder()
        f_gulf_of_bothnia = b.move(b.russia, UnitType.FLEET, b.gulf_of_bothnia, b.st_petersburg_nc)

        b.assertIllegal(f_gulf_of_bothnia)
        b.moves_adjudicate(self)

    def test_6_b_4(self):
        """ 6.B.4. TEST CASE, SUPPORT TO UNREACHABLE COAST ALLOWED
            A fleet can give support to a coast where it can not go.
            France: F Gascony - Spain(nc)
            France: F Marseilles Supports F Gascony - Spain(nc)
            Italy: F Western Mediterranean - Spain(sc)
            Although the fleet in Marseilles can not go to the north coast it can still
            support targeting the north coast. So, the support is successful, the move of the fleet
            in Gasgony succeeds and the move of the Italian fleet fails.
        """
        b = BoardBuilder()
        f_gascony = b.move(b.france, UnitType.FLEET, b.gascony_c, b.spain_nc)
        f_marseilles = b.supportMove(b.france, UnitType.FLEET, b.marseilles_c, f_gascony, b.spain_nc)
        f_western_mediterranean = b.move(b.italy, UnitType.FLEET, b.western_mediterranean, b.spain_sc)

        b.assertSuccess(f_gascony)
        b.assertSuccess(f_marseilles)
        b.assertFail(f_western_mediterranean)
        b.moves_adjudicate(self)

    def test_6_b_5(self):
        """ 6.B.5. TEST CASE, SUPPORT FROM UNREACHABLE COAST NOT ALLOWED
            A fleet can not give support to an area that can not be reached from the current coast of the fleet.
            France: F Marseilles - Gulf of Lyon
            France: F Spain(nc) Supports F Marseilles - Gulf of Lyon
            Italy: F Gulf of Lyon Hold
            The Gulf of Lyon can not be reached from the North Coast of Spain. Therefore, the support of
            Spain is invalid and the fleet in the Gulf of Lyon is not dislodged.
        """
        b = BoardBuilder()
        f_marseilles = b.move(b.france, UnitType.FLEET, b.marseilles_c, b.gulf_of_lyon)
        f_spain_nc = b.supportMove(b.france, UnitType.FLEET, b.spain_nc, f_marseilles, b.gulf_of_lyon)
        f_gulf_of_lyon = b.hold(b.italy, UnitType.FLEET, b.gulf_of_lyon)

        b.assertIllegal(f_spain_nc)
        b.assertFail(f_marseilles)
        b.moves_adjudicate(self)
    
    def test_6_b_6(self):
        """ 6.B.6. TEST CASE, SUPPORT CAN BE CUT WITH OTHER COAST
            Support can be cut from the other coast.
            England: F Irish Sea Supports F North Atlantic Ocean - Mid-Atlantic Ocean
            England: F North Atlantic Ocean - Mid-Atlantic Ocean
            France: F Spain(nc) Supports F Mid-Atlantic Ocean
            France: F Mid-Atlantic Ocean Hold
            Italy: F Gulf of Lyon - Spain(sc)
            The Italian fleet in the Gulf of Lyon will cut the support in Spain. That means
            that the French fleet in the Mid Atlantic Ocean will be dislodged by the English fleet
            in the North Atlantic Ocean.
        """
        b = BoardBuilder()
        f_north_atlantic_ocean = b.move(b.england, UnitType.FLEET, b.north_atlantic_ocean, b.mid_atlantic_ocean)
        f_irish_sea = b.supportMove(b.england, UnitType.FLEET, b.irish_sea, f_north_atlantic_ocean, b.mid_atlantic_ocean)
        f_mid_atlantic_ocean = b.hold(b.france, UnitType.FLEET, b.mid_atlantic_ocean)
        f_spain_nc = b.supportHold(b.france, UnitType.FLEET, b.spain_nc, f_mid_atlantic_ocean)
        f_gulf_of_lyon = b.move(b.italy, UnitType.FLEET, b.gulf_of_lyon, b.spain_sc)

        b.assertFail(f_gulf_of_lyon)
        b.assertFail(f_spain_nc)
        b.assertSuccess(f_north_atlantic_ocean)
        b.assertDislodge(f_mid_atlantic_ocean)
        b.moves_adjudicate(self)

    # NOT APPLICABLE 6_b_7; TEST CASE, SUPPORTING WITH UNSPECIFIED COAST

    # NOT APPLICABLE 6_b_8; TEST CASE, SUPPORTING WITH UNSPECIFIED COAST WHEN ONLY ONE COAST IS POSSIBLE

    # NOT APPLICABLE 6_b_9; TEST CASE, SUPPORTING WITH WRONG COAST

    # NOT APPLICABLE 6_b_10; TEST CASE, UNIT ORDERED WITH WRONG COAST

    # NOT APPLICABLE 6_b_11; TEST CASE, COAST CAN NOT BE ORDERED TO CHANGE

    # NOT APPLICABLE 6_b_12; TEST CASE, ARMY MOVEMENT WITH COASTAL SPECIFICATION

    def test_6_b_13(self):
        """ 6.B.13. TEST CASE, COASTAL CRAWL NOT ALLOWED
            If a fleet is leaving a sector from a certain coast while in the opposite direction another fleet
            is moving to another coast of the sector, it is still a head to head battle. This has been decided in
            the great revision of the 1961 rules that resulted in the 1971 rules.
            Turkey: F Bulgaria(sc) - Constantinople
            Turkey: F Constantinople - Bulgaria(ec)
            Both moves fail.
        """
        b = BoardBuilder()
        f_bulgaria_sc = b.move(b.turkey, UnitType.FLEET, b.bulgaria_sc, b.constantinople_c)
        f_constantinople = b.move(b.turkey, UnitType.FLEET, b.constantinople_c, b.bulgaria_ec)
        
        b.assertFail(f_bulgaria_sc)
        b.assertFail(f_constantinople)
        b.moves_adjudicate(self)

    # NOT APPLICABLE 6_b_14; TEST CASE, BUILDING WITH UNSPECIFIED COAST

    def test_6_c_1(self):
        """ 6.C.1. TEST CASE, THREE ARMY CIRCULAR MOVEMENT
            Three units can change place, even in spring 1901.
            Turkey: F Ankara - Constantinople
            Turkey: A Constantinople - Smyrna
            Turkey: A Smyrna - Ankara
            All three units will move.
        """
        b = BoardBuilder()
        f_ankara = b.move(b.turkey, UnitType.FLEET, b.ankara_c, b.constantinople_c)
        a_constantinople = b.move(b.turkey, UnitType.ARMY, b.constantinople, b.smyrna)
        a_smyrna = b.move(b.turkey, UnitType.ARMY, b.smyrna, b.ankara)
        
        b.assertSuccess(f_ankara, a_constantinople, a_smyrna)
        b.moves_adjudicate(self)

    def test_6_c_2(self):
        """ 6.C.2. TEST CASE, THREE ARMY CIRCULAR MOVEMENT WITH SUPPORT
            Three units can change place, even when one gets support.
            Turkey: F Ankara - Constantinople
            Turkey: A Constantinople - Smyrna
            Turkey: A Smyrna - Ankara
            Turkey: A Bulgaria Supports F Ankara - Constantinople
            Of course the three units will move, but knowing how programs are written, this can confuse the adjudicator.
        """
        b = BoardBuilder()
        f_ankara = b.move(b.turkey, UnitType.FLEET, b.ankara_c, b.constantinople_c)
        a_constantinople = b.move(b.turkey, UnitType.ARMY, b.constantinople, b.smyrna)
        a_smyrna = b.move(b.turkey, UnitType.ARMY, b.smyrna, b.ankara)
        a_bulgaria = b.supportMove(b.turkey, UnitType.ARMY, b.bulgaria, f_ankara, b.constantinople_c)

        b.assertSuccess(f_ankara, a_constantinople, a_smyrna, a_bulgaria)
        b.moves_adjudicate(self)

    def test_6_c_3(self):
        """ 6.C.3. TEST CASE, A DISRUPTED THREE ARMY CIRCULAR MOVEMENT
            When one of the units bounces, the whole circular movement will hold.
            Turkey: F Ankara - Constantinople
            Turkey: A Constantinople - Smyrna
            Turkey: A Smyrna - Ankara
            Turkey: A Bulgaria - Constantinople
            Every unit will keep its place.
        """
        b = BoardBuilder()
        f_ankara = b.move(b.turkey, UnitType.FLEET, b.ankara_c, b.constantinople_c)
        a_constantinople = b.move(b.turkey, UnitType.ARMY, b.constantinople, b.smyrna)
        a_smyrna = b.move(b.turkey, UnitType.ARMY, b.smyrna, b.ankara)
        a_bulgaria = b.move(b.turkey, UnitType.ARMY, b.bulgaria, b.constantinople_c)

        b.assertFail(f_ankara, a_constantinople, a_smyrna, a_bulgaria)
        b.moves_adjudicate(self)

    def test_6_c_4(self):
        """ 6.C.4. TEST CASE, A CIRCULAR MOVEMENT WITH ATTACKED CONVOY
            When the circular movement contains an attacked convoy, the circular movement succeeds.
            The adjudication algorithm should handle attack of convoys before calculating circular movement.
            Austria: A Trieste - Serbia
            Austria: A Serbia - Bulgaria
            Turkey: A Bulgaria - Trieste
            Turkey: F Aegean Sea Convoys A Bulgaria - Trieste
            Turkey: F Ionian Sea Convoys A Bulgaria - Trieste
            Turkey: F Adriatic Sea Convoys A Bulgaria - Trieste
            Italy: F Naples - Ionian Sea
            The fleet in the Ionian Sea is attacked but not dislodged. The circular movement succeeds.
            The Austrian and Turkish armies will advance.
        """
        b = BoardBuilder()
        a_trieste = b.move(b.austria, UnitType.ARMY, b.trieste, b.serbia)
        a_serbia = b.move(b.austria, UnitType.ARMY, b.serbia, b.bulgaria)
        a_bulgaria = b.move(b.turkey, UnitType.ARMY, b.bulgaria, b.trieste)
        f_aegean_sea = b.convoy(b.turkey, b.aegean_sea, a_bulgaria, b.trieste)
        f_ionian_sea = b.convoy(b.turkey, b.ionian_sea, a_bulgaria, b.trieste)
        f_adriatic_sea = b.convoy(b.turkey, b.adriatic_sea, a_bulgaria, b.trieste)
        f_naples = b.move(b.italy, UnitType.FLEET, b.naples_c, b.ionian_sea)

        b.assertSuccess(a_trieste, a_serbia, a_bulgaria, f_aegean_sea, f_ionian_sea, f_adriatic_sea)
        b.assertFail(f_naples)
        b.moves_adjudicate(self)

    def test_6_c_5(self):
        """ 6.C.5. TEST CASE, A DISRUPTED CIRCULAR MOVEMENT DUE TO DISLODGED CONVOY
            When the circular movement contains a convoy, the circular movement is disrupted when the convoying
            fleet is dislodged. The adjudication algorithm should disrupt convoys before calculating circular movement.
            Austria: A Trieste - Serbia
            Austria: A Serbia - Bulgaria
            Turkey: A Bulgaria - Trieste
            Turkey: F Aegean Sea Convoys A Bulgaria - Trieste
            Turkey: F Ionian Sea Convoys A Bulgaria - Trieste
            Turkey: F Adriatic Sea Convoys A Bulgaria - Trieste
            Italy: F Naples - Ionian Sea
            Italy: F Tunis Supports F Naples - Ionian Sea
            Due to the dislodged convoying fleet, all Austrian and Turkish armies will not move.
        """
        b = BoardBuilder()
        a_trieste = b.move(b.austria, UnitType.ARMY, b.trieste, b.serbia)
        a_serbia = b.move(b.austria, UnitType.ARMY, b.serbia, b.bulgaria)
        a_bulgaria = b.move(b.turkey, UnitType.ARMY, b.bulgaria, b.trieste)

        f_aegean_sea = b.convoy(b.turkey, b.aegean_sea, a_bulgaria, b.trieste)
        f_ionian_sea = b.convoy(b.turkey, b.ionian_sea, a_bulgaria, b.trieste)
        f_adriatic_sea = b.convoy(b.turkey, b.adriatic_sea, a_bulgaria, b.trieste)

        f_naples = b.move(b.italy, UnitType.FLEET, b.naples_c, b.ionian_sea)
        f_tunis = b.supportMove(b.italy, UnitType.FLEET, b.tunis_c, f_naples, b.ionian_sea)
        b.assertFail(a_trieste, a_serbia, a_bulgaria, f_ionian_sea)
        b.assertSuccess(f_naples, f_tunis, f_aegean_sea, f_adriatic_sea)
        b.moves_adjudicate(self)

    def test_6_c_6(self):
        """ 6.C.6. TEST CASE, TWO ARMIES WITH TWO CONVOYS
            Two armies can swap places even when they are not adjacent.
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            France: F English Channel Convoys A Belgium - London
            France: A Belgium - London
            Both convoys should succeed.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.belgium)
        a_belgium = b.move(b.france, UnitType.ARMY, b.belgium, b.london)
        f_english_channel = b.convoy(b.england, b.english_channel, a_belgium, b.london)
        
        b.assertSuccess(a_london, f_north_sea, a_belgium, f_english_channel)
        b.moves_adjudicate(self)

    def test_6_c_7(self):
        """ 6.C.7. TEST CASE, DISRUPTED UNIT SWAP
            If in a swap one of the unit bounces, then the swap fails.
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            France: F English Channel Convoys A Belgium - London
            France: A Belgium - London
            France: A Burgundy - Belgium
            None of the units will succeed to move.
    """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.belgium)
        a_belgium = b.move(b.france, UnitType.ARMY, b.belgium, b.london)
        f_english_channel = b.convoy(b.england, b.english_channel, a_belgium, b.london)
        a_burgundy = b.move(b.france, UnitType.ARMY, b.burgundy, b.belgium)

        b.assertSuccess(f_north_sea, f_english_channel)
        b.assertFail(a_london, a_belgium, a_burgundy)
        b.moves_adjudicate(self)

    def test_6_d_1(self):
        """ 6.D.1. TEST CASE, SUPPORTED HOLD CAN PREVENT DISLODGEMENT
            The most simple support to hold order.
            Austria: F Adriatic Sea Supports A Trieste - Venice
            Austria: A Trieste - Venice
            Italy: A Venice Hold
            Italy: A Tyrolia Supports A Venice
            The support of Tyrolia prevents that the army in Venice is dislodged. The army in Trieste will not move.
        """
        b = BoardBuilder()
        a_trieste = b.move(b.austria, UnitType.ARMY, b.trieste, b.venice)
        f_adriatic_sea = b.supportMove(b.austria, UnitType.FLEET, b.adriatic_sea, a_trieste, b.venice)
        a_venice = b.hold(b.italy, UnitType.ARMY, b.venice)
        a_tyrolia = b.supportHold(b.italy, UnitType.ARMY, b.tyrolia, a_venice)

        b.assertNotDislodge(a_venice)
        b.assertSuccess(f_adriatic_sea, a_tyrolia)
        b.assertFail(a_trieste)
        b.moves_adjudicate(self)
        
    def test_6_d_2(self):
        """ 6.D.2. TEST CASE, A MOVE CUTS SUPPORT ON HOLD
            The most simple support on hold cut.
            Austria: F Adriatic Sea Supports A Trieste - Venice
            Austria: A Trieste - Venice
            Austria: A Vienna - Tyrolia
            Italy: A Venice Hold
            Italy: A Tyrolia Supports A Venice
            The support of Tyrolia is cut by the army in Vienna. That means that the army in Venice is dislodged by the
            army from Trieste.
        """
        b = BoardBuilder()
        a_trieste = b.move(b.austria, UnitType.ARMY, b.trieste, b.venice)
        f_adriatic_sea = b.supportMove(b.austria, UnitType.FLEET, b.adriatic_sea, a_trieste, b.venice)
        a_vienna = b.move(b.austria, UnitType.ARMY, b.vienna, b.tyrolia)
        a_venice = b.hold(b.italy, UnitType.ARMY, b.venice)
        a_tyrolia = b.supportHold(b.italy, UnitType.ARMY, b.tyrolia, a_venice)

        b.assertDislodge(a_venice)
        b.assertSuccess(a_trieste)
        b.assertFail(a_vienna)
        b.moves_adjudicate(self)

    def test_6_d_3(self):
        """ 6.D.3. TEST CASE, A MOVE CUTS SUPPORT ON MOVE
            The most simple support on move cut.
            Austria: F Adriatic Sea Supports A Trieste - Venice
            Austria: A Trieste - Venice
            Italy: A Venice Hold
            Italy: F Ionian Sea - Adriatic Sea
            The support of the fleet in the Adriatic Sea is cut. That means that the army in Venice will not be
            dislodged and the army in Trieste stays in Trieste.
        """
        b = BoardBuilder()
        a_trieste = b.move(b.austria, UnitType.ARMY, b.trieste, b.venice)
        f_adriatic_sea = b.supportMove(b.austria, UnitType.FLEET, b.adriatic_sea, a_trieste, b.venice)
        a_venice = b.hold(b.italy, UnitType.ARMY, b.venice)
        f_ionian_sea = b.move(b.italy, UnitType.FLEET, b.ionian_sea, b.adriatic_sea)

        b.assertNotDislodge(a_venice)
        b.assertFail(a_trieste, f_ionian_sea, f_adriatic_sea)
        b.moves_adjudicate(self)

    def test_6_d_4(self):
        """ 6.D.4. TEST CASE, SUPPORT TO HOLD ON UNIT SUPPORTING A HOLD ALLOWED
            A unit that is supporting a hold, can receive a hold support.
            Germany: A Berlin Supports F Kiel
            Germany: F Kiel Supports A Berlin
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            The Russian move from Prussia to Berlin fails.
        """
        b = BoardBuilder()
        a_berlin = b.army(b.berlin, b.germany)
        f_kiel = b.fleet(b.kiel_c, b.germany)
        a_berlin.order = Support(f_kiel, b.kiel_c)
        f_kiel.order = Support(a_berlin, b.berlin)
        a_prussia = b.move(b.russia, UnitType.ARMY, b.prussia, b.berlin)
        f_baltic_sea = b.supportMove(b.russia, UnitType.FLEET, b.baltic_sea, a_prussia, b.berlin)

        b.assertFail(a_prussia, a_berlin)
        b.assertSuccess(f_kiel)
        b.moves_adjudicate(self)
        
    def test_6_d_5(self):
        """ 6.D.5. TEST CASE, SUPPORT TO HOLD ON UNIT SUPPORTING A MOVE ALLOWED
            A unit that is supporting a move, can receive a hold support.
            Germany: A Berlin Supports A Munich - Silesia
            Germany: F Kiel Supports A Berlin
            Germany: A Munich - Silesia
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            The Russian move from Prussia to Berlin fails.
        """
        b = BoardBuilder()
        a_munich = b.move(b.germany, UnitType.ARMY, b.munich, b.silesia)
        a_berlin = b.supportMove(b.germany, UnitType.ARMY, b.berlin, a_munich, b.silesia)
        f_kiel = b.supportHold(b.germany, UnitType.FLEET, b.kiel_c, a_berlin)
        a_berlin.order = Support(f_kiel, b.kiel_c)
        f_kiel.order = Support(a_berlin, b.berlin)
        a_prussia = b.move(b.russia, UnitType.ARMY, b.prussia, b.berlin)
        f_baltic_sea = b.supportMove(b.russia, UnitType.FLEET, b.baltic_sea, a_prussia, b.berlin)

        b.assertFail(a_berlin, a_prussia)
        b.assertSuccess(f_kiel, a_munich)
        b.moves_adjudicate(self)

    def test_6_d_6(self):
        """ 6.D.6. TEST CASE, SUPPORT TO HOLD ON CONVOYING UNIT ALLOWED
            A unit that is convoying, can receive a hold support.
            Germany: A Berlin - Sweden
            Germany: F Baltic Sea Convoys A Berlin - Sweden
            Germany: F Prussia Supports F Baltic Sea
            Russia: F Livonia - Baltic Sea
            Russia: F Gulf of Bothnia Supports F Livonia - Baltic Sea
            The Russian move from Livonia to the Baltic Sea fails. The convoy from Berlin to Sweden succeeds.
        """
        b = BoardBuilder()
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.sweden)
        f_baltic_sea = b.convoy(b.germany, b.baltic_sea, a_berlin, b.sweden)
        f_prussia = b.supportHold(b.germany, UnitType.FLEET, b.prussia_c, f_baltic_sea)
        f_livonia = b.move(b.russia, UnitType.FLEET, b.livonia_c, b.baltic_sea)
        f_gulf_of_bothnia = b.supportMove(b.russia, UnitType.FLEET, b.gulf_of_bothnia, f_livonia, b.baltic_sea)
        
        b.assertFail(f_livonia)
        b.assertSuccess(f_prussia, f_baltic_sea, a_berlin)
        b.moves_adjudicate(self)

    def test_6_d_7(self):
        """ 6.D.7. TEST CASE, SUPPORT TO HOLD ON MOVING UNIT NOT ALLOWED
            A unit that is moving, can not receive a hold support for the situation that the move fails.
            Germany: F Baltic Sea - Sweden
            Germany: F Prussia Supports F Baltic Sea
            Russia: F Livonia - Baltic Sea
            Russia: F Gulf of Bothnia Supports F Livonia - Baltic Sea
            Russia: A Finland - Sweden
            The support of the fleet in Prussia fails. The fleet in Baltic Sea will bounce on the Russian army
            in Finland and will be dislodged by the Russian fleet from Livonia when it returns to the Baltic Sea.
        """
        b = BoardBuilder()
        f_baltic_sea = b.move(b.germany, UnitType.FLEET, b.baltic_sea, b.sweden_c)
        f_prussia = b.supportHold(b.germany, UnitType.FLEET, b.prussia_c, f_baltic_sea)
        f_livonia = b.move(b.russia, UnitType.FLEET, b.livonia_c, b.baltic_sea)
        f_gulf_of_bothnia = b.supportMove(b.russia, UnitType.FLEET, b.gulf_of_bothnia, f_livonia, b.baltic_sea)
        a_finland = b.move(b.russia, UnitType.ARMY, b.finland, b.sweden)

        b.assertFail(a_finland, f_baltic_sea)
        b.assertIllegal(f_prussia)
        b.assertSuccess(f_livonia)
        b.assertDislodge(f_baltic_sea)
        b.moves_adjudicate(self)

    def test_6_d_8(self):
        """ 6.D.8. TEST CASE, FAILED CONVOY CAN NOT RECEIVE HOLD SUPPORT
            If a convoy fails because of disruption of the convoy or when the right convoy orders are not given,
            then the army to be convoyed can not receive support in hold, since it still tried to move.
            Austria: F Ionian Sea Hold
            Austria: A Serbia Supports A Albania - Greece
            Austria: A Albania - Greece
            Turkey: A Greece - Naples
            Turkey: A Bulgaria Supports A Greece
            There was a possible convoy from Greece to Naples, before the orders were made public (via the Ionian Sea).
            This means that the order of Greece to Naples should never be treated as illegal order and be changed in a
            hold order able to receive hold support (see also issue VI.A). Therefore, the support in Bulgaria fails and
            the army in Greece is dislodged by the army in Albania.
        """
        b = BoardBuilder()
        f_ionian_sea = b.hold(b.austria, UnitType.FLEET, b.ionian_sea)
        a_albania = b.move(b.austria, UnitType.ARMY, b.albania, b.greece)
        a_serbia = b.supportMove(b.austria, UnitType.ARMY, b.serbia, a_albania, b.greece)
        a_greece = b.move(b.turkey, UnitType.ARMY, b.greece, b.naples)
        a_bulgaria = b.supportHold(b.turkey, UnitType.ARMY, b.bulgaria, a_greece)

        b.assertNotIllegal(a_greece)
        b.assertSuccess(f_ionian_sea, a_albania, a_serbia, a_greece, a_bulgaria)
        b.assertDislodge(a_greece)
        b.moves_adjudicate(self)

    def test_6_d_9(self):
        """ 6.D.9. TEST CASE, SUPPORT TO MOVE ON HOLDING UNIT NOT ALLOWED
            A unit that is holding can not receive a support in moving.
            Italy: A Venice - Trieste
            Italy: A Tyrolia Supports A Venice - Trieste
            Austria: A Albania Supports A Trieste - Serbia
            Austria: A Trieste Hold
            The support of the army in Albania fails and the army in Trieste is dislodged by the army from Venice.
        """
        b = BoardBuilder()
        a_venice = b.move(b.italy, UnitType.ARMY, b.venice, b.trieste)
        a_tyrolia = b.supportMove(b.italy, UnitType.ARMY, b.tyrolia, a_venice, b.trieste)
        a_trieste = b.hold(b.austria, UnitType.ARMY, b.trieste)
        a_albania = b.supportMove(b.austria, UnitType.ARMY, b.albania, a_trieste, b.serbia)

        b.assertIllegal(a_albania)
        b.assertDislodge(a_trieste)
        b.moves_adjudicate(self)

    def test_6_d_10(self):
        """ 6.D.10. TEST CASE, SELF DISLODGMENT PROHIBITED
            A unit may not dislodge a unit of the same great power.
            Germany: A Berlin Hold
            Germany: F Kiel - Berlin
            Germany: A Munich Supports F Kiel - Berlin
            Move to Berlin fails.
        """
        b = BoardBuilder()
        a_berlin = b.hold(b.germany, UnitType.ARMY, b.berlin)
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.berlin_c)
        a_munich = b.supportMove(b.germany, UnitType.ARMY, b.munich, f_kiel, b.berlin_c)

        b.assertFail(f_kiel)
        b.assertSuccess(a_berlin, a_munich)
        b.moves_adjudicate(self)

    def test_6_d_11(self):
        """ 6.D.11. TEST CASE, NO SELF DISLODGMENT OF RETURNING UNIT
            Idem.
            Germany: A Berlin - Prussia
            Germany: F Kiel - Berlin
            Germany: A Munich Supports F Kiel - Berlin
            Russia: A Warsaw - Prussia
            Army in Berlin bounces, but is not dislodged by own unit.
        """
        b = BoardBuilder()
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.prussia)
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.berlin_c)
        a_munich = b.supportMove(b.germany, UnitType.ARMY, b.munich, f_kiel, b.berlin_c)
        a_prussia = b.move(b.russia, UnitType.ARMY, b.warsaw, b.prussia)

        b.assertFail(f_kiel, a_berlin, a_prussia)
        b.assertSuccess(a_munich)
        b.assertNotDislodge(a_berlin)
        b.moves_adjudicate(self)

    def test_6_d_12(self):
        """ 6.D.12. TEST CASE, SUPPORTING A FOREIGN UNIT TO DISLODGE OWN UNIT PROHIBITED
            You may not help another power in dislodging your own unit.
            Austria: F Trieste Hold
            Austria: A Vienna Supports A Venice - Trieste
            Italy: A Venice - Trieste
            No dislodgment of fleet in Trieste.
        """
        b = BoardBuilder()
        a_venice = b.move(b.italy, UnitType.ARMY, b.venice, b.trieste)
        f_trieste = b.hold(b.austria, UnitType.FLEET, b.trieste_c)
        a_vienna = b.supportMove(b.austria, UnitType.ARMY, b.vienna, a_venice, b.trieste)

        b.assertFail(a_venice)
        b.assertNotDislodge(f_trieste)
        b.moves_adjudicate(self)

    def test_6_d_13(self):
        """ 6.D.13. TEST CASE, SUPPORTING A FOREIGN UNIT TO DISLODGE A RETURNING OWN UNIT PROHIBITED
            Idem.
            Austria: F Trieste - Adriatic Sea
            Austria: A Vienna Supports A Venice - Trieste
            Italy: A Venice - Trieste
            Italy: F Apulia - Adriatic Sea
            No dislodgment of fleet in Trieste.
        """
        b = BoardBuilder()
        a_venice = b.move(b.italy, UnitType.ARMY, b.venice, b.trieste)
        f_apulia = b.move(b.italy, UnitType.FLEET, b.apulia_c, b.adriatic_sea)
        f_trieste = b.move(b.austria, UnitType.FLEET, b.trieste_c, b.adriatic_sea)
        a_vienna = b.supportMove(b.austria, UnitType.ARMY, b.vienna, a_venice, b.trieste)

        b.assertFail(a_venice, f_trieste, f_apulia)
        b.assertNotDislodge(f_trieste)
        b.moves_adjudicate(self)

    def test_6_d_14(self):
        """  6.D.14. TEST CASE, SUPPORTING A FOREIGN UNIT IS NOT ENOUGH TO PREVENT DISLODGEMENT
            If a foreign unit has enough support to dislodge your unit, you may not prevent that dislodgement by
            supporting the attack.
            Austria: F Trieste Hold
            Austria: A Vienna Supports A Venice - Trieste
            Italy: A Venice - Trieste
            Italy: A Tyrolia Supports A Venice - Trieste
            Italy: F Adriatic Sea Supports A Venice - Trieste
            The fleet in Trieste is dislodged.
        """
        b = BoardBuilder()
        f_trieste = b.hold(b.austria, UnitType.FLEET, b.trieste_c)
        a_venice = b.move(b.italy, UnitType.ARMY, b.venice, b.trieste)
        a_vienna = b.supportMove(b.austria, UnitType.ARMY, b.vienna, a_venice, b.trieste)
        a_tyrolia = b.supportMove(b.italy, UnitType.ARMY, b.tyrolia, a_venice, b.trieste)
        f_adriatic_sea = b.supportMove(b.italy, UnitType.FLEET, b.adriatic_sea, a_venice, b.trieste)

        b.assertDislodge(f_trieste)
        b.assertSuccess(a_venice, a_vienna, f_trieste, a_tyrolia, f_adriatic_sea)
        b.moves_adjudicate(self)

    def test_6_d_15(self):
        """ 6.D.15. TEST CASE, DEFENDER CAN NOT CUT SUPPORT FOR ATTACK ON ITSELF
            A unit that is attacked by a supported unit can not prevent dislodgement by guessing which of the units
            will do the support.
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Turkey: F Ankara - Constantinople
            The support of Constantinople is not cut and the fleet in Ankara is dislodged by the fleet in the Black Sea.
        """
        b = BoardBuilder()
        f_black_sea = b.move(b.russia, UnitType.FLEET, b.black_sea, b.ankara_c)
        f_constantinople = b.supportMove(b.russia, UnitType.FLEET, b.constantinople_c, f_black_sea, b.ankara_c)
        f_ankara = b.move(b.turkey, UnitType.FLEET, b.ankara_c, b.constantinople_c)

        b.assertSuccess(f_constantinople, f_black_sea)
        b.assertFail(f_ankara)
        b.assertDislodge(f_ankara)
        b.moves_adjudicate(self)

    def test_6_d_16(self):
        """ 6.D.16. TEST CASE, CONVOYING A UNIT DISLODGING A UNIT OF SAME POWER IS ALLOWED
            It is allowed to convoy a foreign unit that dislodges your own unit is allowed.
            England: A London Hold
            England: F North Sea Convoys A Belgium - London
            France: F English Channel Supports A Belgium - London
            France: A Belgium - London
            The English army in London is dislodged by the French army coming from Belgium.
        """
        b = BoardBuilder()
        a_london = b.hold(b.england, UnitType.ARMY, b.london)
        a_belgium = b.move(b.france, UnitType.ARMY, b.belgium, b.london)
        f_north_sea = b.convoy(b.england, b.north_sea, a_belgium, b.london)
        f_english_channel = b.supportMove(b.france, UnitType.FLEET, b.english_channel, a_belgium, b.london)

        b.assertDislodge(a_london)
        b.assertSuccess(a_london, a_belgium, f_north_sea, f_english_channel)
        b.moves_adjudicate(self)

    def test_6_d_17(self):
        """ 6.D.17. TEST CASE, DISLODGEMENT CUTS SUPPORTS
            The famous dislodge rule.
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Turkey: F Ankara - Constantinople
            Turkey: A Smyrna Supports F Ankara - Constantinople
            Turkey: A Armenia - Ankara
            The Russian fleet in Constantinople is dislodged. This cuts the support to from Black Sea to Ankara.
            Black Sea will bounce with the army from Armenia.
        """
        b = BoardBuilder()
        f_black_sea = b.move(b.russia, UnitType.FLEET, b.black_sea, b.ankara_c)
        f_constantinople = b.supportMove(b.russia, UnitType.FLEET, b.constantinople_c, f_black_sea, b.ankara_c)
        f_ankara = b.move(b.turkey, UnitType.FLEET, b.ankara_c, b.constantinople_c)
        a_smyrna = b.supportMove(b.turkey, UnitType.ARMY, b.smyrna, f_ankara, b.constantinople_c)
        a_armenia = b.move(b.turkey, UnitType.ARMY, b.armenia, b.ankara)
        
        b.assertDislodge(f_constantinople)
        b.assertFail(f_black_sea, a_armenia)
        b.moves_adjudicate(self)

    def test_6_d_18(self):
        """ 6.D.18. TEST CASE, A SURVIVING UNIT WILL SUSTAIN SUPPORT
            Idem. But now with an additional hold that prevents dislodgement.
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Russia: A Bulgaria Supports F Constantinople
            Turkey: F Ankara - Constantinople
            Turkey: A Smyrna Supports F Ankara - Constantinople
            Turkey: A Armenia - Ankara
            The Russian fleet in the Black Sea will dislodge the Turkish fleet in Ankara.
        """
        b = BoardBuilder()
        f_black_sea = b.move(b.russia, UnitType.FLEET, b.black_sea, b.ankara_c)
        f_constantinople = b.supportMove(b.russia, UnitType.FLEET, b.constantinople_c, f_black_sea, b.ankara_c)
        a_bulgaria = b.supportHold(b.russia, UnitType.ARMY, b.bulgaria, f_constantinople)
        f_ankara = b.move(b.turkey, UnitType.FLEET, b.ankara_c, b.constantinople_c)
        a_smyrna = b.supportMove(b.turkey, UnitType.ARMY, b.smyrna, f_ankara, b.constantinople_c)
        a_armenia = b.move(b.turkey, UnitType.ARMY, b.armenia, b.ankara)

        b.assertDislodge(f_ankara)
        b.assertFail(a_armenia)
        b.assertSuccess(a_bulgaria, a_smyrna, f_constantinople)
        b.moves_adjudicate(self)

    def test_6_d_19(self):
        """ 6.D.19. TEST CASE, EVEN WHEN SURVIVING IS IN ALTERNATIVE WAY
            Now, the dislodgement is prevented because the supports comes from a Russian army:
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Russia: A Smyrna Supports F Ankara - Constantinople
            Turkey: F Ankara - Constantinople
            The Russian fleet in Constantinople is not dislodged, because one of the support is of Russian origin.
            The support from Black Sea to Ankara will sustain and the fleet in Ankara will be dislodged.
        """        
        b = BoardBuilder()
        f_black_sea = b.move(b.russia, UnitType.FLEET, b.black_sea, b.ankara_c)
        f_constantinople = b.supportMove(b.russia, UnitType.FLEET, b.constantinople_c, f_black_sea, b.ankara_c)
        f_ankara = b.move(b.turkey, UnitType.FLEET, b.ankara_c, b.constantinople_c)
        a_smyrna = b.supportMove(b.russia, UnitType.ARMY, b.smyrna, f_ankara, b.constantinople_c)

        b.assertDislodge(f_ankara)
        b.assertNotDislodge(f_constantinople)
        b.assertSuccess(a_smyrna, f_black_sea, f_constantinople)
        b.moves_adjudicate(self)

    def test_6_d_20(self):
        """ 6.D.20. TEST CASE, UNIT CAN NOT CUT SUPPORT OF ITS OWN COUNTRY
            Although this is not mentioned in all rulebooks, it is generally accepted that when a unit attacks
            another unit of the same Great Power, it will not cut support.
            England: F London Supports F North Sea - English Channel
            England: F North Sea - English Channel
            England: A Yorkshire - London
            France: F English Channel Hold
            The army in York does not cut support. This means that the fleet in the English Channel is dislodged by the
            fleet in the North Sea.
        """
        b = BoardBuilder()
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.english_channel)
        f_london = b.supportMove(b.england, UnitType.FLEET, b.london_c, f_north_sea, b.english_channel)
        a_yorkshire = b.move(b.england, UnitType.ARMY, b.yorkshire, b.london)
        f_english_channel = b.hold(b.france, UnitType.FLEET, b.english_channel)

        b.assertFail(a_yorkshire)
        b.assertSuccess(f_london, f_north_sea)
        b.assertDislodge(f_english_channel)
        b.moves_adjudicate(self)

    def test_6_d_21(self):
        """ 6.D.21. TEST CASE, DISLODGING DOES NOT CANCEL A SUPPORT CUT
            Sometimes there is the question whether a dislodged moving unit does not cut support (similar to the
            dislodge rule). This is not the case.
            Austria: F Trieste Hold
            Italy: A Venice - Trieste
            Italy: A Tyrolia Supports A Venice - Trieste
            Germany: A Munich - Tyrolia
            Russia: A Silesia - Munich
            Russia: A Berlin Supports A Silesia - Munich
            Although the German army is dislodged, it still cuts the Italian support. That means that the Austrian
            Fleet is not dislodged.
        """
        b = BoardBuilder()
        f_trieste = b.hold(b.austria, UnitType.FLEET, b.trieste_c)
        a_venice = b.move(b.italy, UnitType.ARMY, b.venice, b.trieste)
        a_tyrolia = b.supportMove(b.italy, UnitType.ARMY, b.tyrolia, a_venice, b.trieste)
        a_munich = b.move(b.germany, UnitType.ARMY, b.munich, b.tyrolia)
        a_silesia = b.move(b.russia, UnitType.ARMY, b.silesia, b.munich)
        a_berlin = b.supportMove(b.russia, UnitType.ARMY, b.berlin, a_silesia, b.munich)

        b.assertDislodge(a_munich)
        b.assertFail(a_tyrolia, a_venice, a_munich)
        b.assertSuccess(a_berlin, a_silesia)
        b.assertNotDislodge(f_trieste)
        b.moves_adjudicate(self)

    def test_6_d_22(self):
        """ 6.D.22. TEST CASE, IMPOSSIBLE FLEET MOVE CAN NOT BE SUPPORTED
            If a fleet tries moves to a land area it seems pointless to support the fleet, since the move will fail
            anyway. However, in such case, the support is also invalid for defense purposes.
            Germany: F Kiel - Munich
            Germany: A Burgundy Supports F Kiel - Munich
            Russia: A Munich - Kiel
            Russia: A Berlin Supports A Munich - Kiel
            The German move from Kiel to Munich is illegal (fleets can not go to Munich). Therefore, the support from
            Burgundy fails and the Russian army in Munich will dislodge the fleet in Kiel. Note that the failing of the
            support is not explicitly mentioned in the rulebooks (the DPTG is more clear about this point). If you take
            the rulebooks very literally, you might conclude that the fleet in Munich is not dislodged, but this is an
            incorrect interpretation.
        """
        b = BoardBuilder()
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.munich)
        a_burgundy = b.supportMove(b.germany, UnitType.ARMY, b.burgundy, f_kiel, b.munich)
        a_munich = b.move(b.russia, UnitType.ARMY, b.munich, b.kiel)
        a_berlin = b.supportMove(b.russia, UnitType.ARMY, b.berlin, a_munich, b.kiel)

        b.assertIllegal(f_kiel, a_burgundy)
        b.assertSuccess(a_munich, a_berlin)
        b.assertDislodge(f_kiel)
        b.moves_adjudicate(self)

    def test_6_d_23(self):
        """ 6.D.23. TEST CASE, IMPOSSIBLE COAST MOVE CAN NOT BE SUPPORTED
            Comparable with the previous test case, but now the fleet move is impossible for coastal reasons.
            Italy: F Gulf of Lyon - Spain(sc)
            Italy: F Western Mediterranean Supports F Gulf of Lyon - Spain(sc)
            France: F Spain(nc) - Gulf of Lyon
            France: F Marseilles Supports F Spain(nc) - Gulf of Lyon
            The French move from Spain North Coast to Gulf of Lyon is illegal (wrong coast). Therefore, the support
            from Marseilles fails and the fleet in Spain is dislodged.
        """
        b = BoardBuilder()
        f_gulf_of_lyon = b.move(b.italy, UnitType.FLEET, b.gulf_of_lyon, b.spain_sc)
        f_western_mediterranean = b.supportMove(b.italy, UnitType.FLEET, b.western_mediterranean, f_gulf_of_lyon, b.spain_sc)
        f_spain_nc = b.move(b.france, UnitType.FLEET, b.spain_nc, b.gulf_of_lyon)
        f_marseilles = b.supportMove(b.france, UnitType.FLEET, b.marseilles_c, f_spain_nc, b.gulf_of_lyon)

        b.assertIllegal(f_spain_nc, f_marseilles)
        b.assertSuccess(f_gulf_of_lyon, f_western_mediterranean)
        b.assertDislodge(f_spain_nc)
        b.moves_adjudicate(self)

    def test_6_d_24(self):
        """ 6.D.24. TEST CASE, IMPOSSIBLE ARMY MOVE CAN NOT BE SUPPORTED
            Comparable with the previous test case, but now an army tries to move into sea and the support is used in a
            beleaguered garrison.
            France: A Marseilles - Gulf of Lyon
            France: F Spain(sc) Supports A Marseilles - Gulf of Lyon
            Italy: F Gulf of Lyon Hold
            Turkey: F Tyrrhenian Sea Supports F Western Mediterranean - Gulf of Lyon
            Turkey: F Western Mediterranean - Gulf of Lyon
            The French move from Marseilles to Gulf of Lyon is illegal (an army can not go to sea). Therefore,
            the support from Spain fails and there is no beleaguered garrison. The fleet in the Gulf of Lyon is
            dislodged by the Turkish fleet in the Western Mediterranean.
        """
        b = BoardBuilder()
        a_marseilles = b.move(b.france, UnitType.ARMY, b.marseilles, b.gulf_of_lyon)
        a_spain_sc = b.supportMove(b.france, UnitType.FLEET, b.spain_sc, a_marseilles, b.gulf_of_lyon)
        f_gulf_of_lyon = b.hold(b.italy, UnitType.FLEET, b.gulf_of_lyon)
        f_western_mediterranean = b.move(b.turkey, UnitType.FLEET, b.western_mediterranean, b.gulf_of_lyon)
        f_tyrrhenian_sea = b.supportMove(b.turkey, UnitType.FLEET, b.tyrrhenian_sea, f_western_mediterranean, b.gulf_of_lyon)

        b.assertIllegal(a_marseilles, a_spain_sc)
        b.assertDislodge(f_gulf_of_lyon)
        b.assertSuccess(f_western_mediterranean, f_tyrrhenian_sea)
        b.moves_adjudicate(self)

    def test_6_d_25(self):
        """ 6.D.25. TEST CASE, FAILING HOLD SUPPORT CAN BE SUPPORTED
            If an adjudicator fails on one of the previous three test cases, then the bug should be removed with care.
            A failing move can not be supported, but a failing hold support, because of some preconditions (unmatching
            order) can still be supported.
            Germany: A Berlin Supports A Prussia
            Germany: F Kiel Supports A Berlin
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            Although the support of Berlin on Prussia fails (because of unmatching orders), the support of Kiel on
            Berlin is still valid. So, Berlin will not be dislodged.
        """
        b = BoardBuilder()
        a_prussia = b.move(b.russia, UnitType.ARMY, b.prussia, b.berlin)
        f_baltic_sea = b.supportMove(b.russia, UnitType.FLEET, b.baltic_sea, a_prussia, b.berlin)
        a_berlin = b.supportHold(b.germany, UnitType.ARMY, b.berlin, a_prussia)
        f_kiel = b.supportHold(b.germany, UnitType.FLEET, b.kiel_c, a_berlin)

        b.assertIllegal(a_berlin)
        b.assertFail(a_prussia)
        b.assertSuccess(f_kiel, f_baltic_sea)
        b.assertNotDislodge(a_berlin)
        b.moves_adjudicate(self)

    def test_6_d_26(self):
        """ 6.D.26. TEST CASE, FAILING MOVE SUPPORT CAN BE SUPPORTED
            Similar as the previous test case, but now with an unmatched support to move.
            Germany: A Berlin Supports A Prussia - Silesia
            Germany: F Kiel Supports A Berlin
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            Again, Berlin will not be dislodged.
        """
        b = BoardBuilder()
        a_prussia = b.move(b.russia, UnitType.ARMY, b.prussia, b.berlin)
        f_baltic_sea = b.supportMove(b.russia, UnitType.FLEET, b.baltic_sea, a_prussia, b.berlin)
        a_berlin = b.supportMove(b.germany, UnitType.ARMY, b.berlin, a_prussia, b.silesia)
        f_kiel = b.supportHold(b.germany, UnitType.FLEET, b.kiel_c, a_berlin)

        b.assertIllegal(a_berlin)
        b.assertFail(a_prussia)
        b.assertSuccess(f_kiel, f_baltic_sea)
        b.assertNotDislodge(a_berlin)
        b.moves_adjudicate(self)

    def test_6_d_27(self):
        """ 6.D.27. TEST CASE, FAILING CONVOY CAN BE SUPPORTED
            Similar as the previous test case, but now with an unmatched convoy.
            England: F Sweden - Baltic Sea
            England: F Denmark Supports F Sweden - Baltic Sea
            Germany: A Berlin Hold
            Russia: F Baltic Sea Convoys A Berlin - Livonia
            Russia: F Prussia Supports F Baltic Sea
            The convoy order in the Baltic Sea is unmatched and fails. However, the support of Prussia on the Baltic Sea
            is still valid and the fleet in the Baltic Sea is not dislodged.
        """
        b = BoardBuilder()
        f_sweden = b.move(b.england, UnitType.FLEET, b.sweden_c, b.baltic_sea)
        f_denmark = b.supportMove(b.england, UnitType.FLEET, b.denmark_c, f_sweden, b.baltic_sea)
        a_berlin = b.hold(b.germany, UnitType.ARMY, b.berlin)
        f_baltic_sea = b.convoy(b.russia, b.baltic_sea, a_berlin, b.livonia)
        f_prussia = b.supportHold(b.russia, UnitType.FLEET, b.prussia_c, f_baltic_sea)

        b.assertIllegal(f_baltic_sea)
        b.assertSuccess(f_prussia, f_denmark)
        b.assertFail(f_sweden)
        b.assertNotDislodge(f_baltic_sea)
        b.moves_adjudicate(self)

    def test_6_d_28(self):
        """ 6.D.28. TEST CASE, IMPOSSIBLE MOVE AND SUPPORT
            If a move is impossible then it can be treated as "illegal", which makes a hold support possible.
            Austria: A Budapest Supports F Rumania
            Russia: F Rumania - Holland
            Turkey: F Black Sea - Rumania
            Turkey: A Bulgaria Supports F Black Sea - Rumania
            The move of the Russian fleet is impossible. But the question is, whether it is "illegal" (see issue 4.E.1).
            If the move is "illegal" it must be ignored and that makes the hold support of the army in Budapest valid
            and the fleet in Rumania will not be dislodged.
            I prefer that the move is "illegal", which means that the fleet in the Black Sea does not dislodge the
            supported Russian fleet.
        """ 
        b = BoardBuilder()
        f_rumania = b.move(b.russia, UnitType.FLEET, b.rumania_c, b.holland_c)
        a_budapest = b.supportHold(b.austria, UnitType.ARMY, b.budapest, f_rumania)
        f_black_sea = b.move(b.turkey, UnitType.FLEET, b.black_sea, b.rumania_c)
        a_bulgaria = b.supportMove(b.turkey, UnitType.ARMY, b.bulgaria, f_black_sea, b.rumania)

        b.assertIllegal(f_rumania)
        b.assertSuccess(a_budapest)
        b.assertFail(f_black_sea)
        b.assertNotDislodge(f_rumania)
        b.moves_adjudicate(self)

    def test_6_d_29(self):
        """ 6.D.29. TEST CASE, MOVE TO IMPOSSIBLE COAST AND SUPPORT
            Similar to the previous test case, but now the move can be "illegal" because of the wrong coast.
            Austria: A Budapest Supports F Rumania
            Russia: F Rumania - Bulgaria(sc)
            Turkey: F Black Sea - Rumania
            Turkey: A Bulgaria Supports F Black Sea - Rumania
            Again the move of the Russian fleet is impossible. However, some people might correct the coast
            (see issue 4.B.3). If the coast is not corrected, again the question is whether it is "illegal" (see
            issue 4.E.1). If the move is "illegal" it must be ignored and that makes the hold support of the army in
            Budapest valid and the fleet in Rumania will not be dislodged.
            I prefer that unambiguous orders are not changed and that the move is "illegal". That means that the fleet
            in the Black Sea does not dislodge the supported Russian fleet.
        """
        b = BoardBuilder()
        f_rumania = b.move(b.russia, UnitType.FLEET, b.rumania_c, b.bulgaria_sc)
        a_budapest = b.supportHold(b.austria, UnitType.ARMY, b.budapest, f_rumania)
        f_black_sea = b.move(b.turkey, UnitType.FLEET, b.black_sea, b.rumania_c)
        a_bulgaria = b.supportMove(b.turkey, UnitType.ARMY, b.bulgaria, f_black_sea, b.rumania)

        b.assertIllegal(f_rumania)
        b.assertSuccess(a_budapest)
        b.assertFail(f_black_sea)
        b.assertNotDislodge(f_rumania)
        b.moves_adjudicate(self)

    def test_6_d_30(self):
        """ 6.D.30. TEST CASE, MOVE WITHOUT COAST AND SUPPORT
            Similar to the previous test case, but now the move can be "illegal" because of missing coast.
            Italy: F Aegean Sea Supports F Constantinople
            Russia: F Constantinople - Bulgaria
            Turkey: F Black Sea - Constantinople
            Turkey: A Bulgaria Supports F Black Sea - Constantinople
            Again the order to the Russian fleet is with problems, because it does not specify the coast, while both
            coasts of Bulgaria are possible. If no default coast is taken (see issue 4.B.1), then also here it must be
            decided whether the order is "illegal" (see issue 4.E.1). If the move is "illegal" it must be ignored and
            that makes the hold support of the fleet in the Aegean Sea valid and the Russian fleet will not be
            dislodged. I don't like default coasts and I prefer that the move is "illegal". That means that the fleet
            in the Black Sea does not dislodge the supported Russian fleet.
        """
        b = BoardBuilder()
        f_constantinople = b.move(b.russia, UnitType.FLEET, b.constantinople_c, b.bulgaria)
        f_aegean_sea = b.supportHold(b.italy, UnitType.FLEET, b.aegean_sea, f_constantinople)
        f_black_sea = b.move(b.turkey, UnitType.FLEET, b.black_sea, b.constantinople_c)
        a_bulgaria = b.supportMove(b.turkey, UnitType.ARMY, b.bulgaria, f_black_sea, b.constantinople_c)

        b.assertNotDislodge(f_constantinople)
        b.assertFail(f_black_sea)
        b.assertSuccess(f_aegean_sea, a_bulgaria)
        b.moves_adjudicate(self)

    def test_6_d_31(self):
        """ 6.D.31. TEST CASE, A TRICKY IMPOSSIBLE SUPPORT
            A support order can be impossible for complex reasons.
            Austria: A Rumania - Armenia
            Turkey: F Black Sea Supports A Rumania - Armenia
            Although the army in Rumania can move to Armenia and the fleet in the Black Sea can also go to Armenia,
            the support is still not possible. The reason is that the only possible convoy is through the Black Sea and
            a fleet can not convoy and support at the same time.
            This is relevant for computer programs that show only the possible orders. In the list of possible orders,
            the support as given to the fleet in the Black Sea, should not be listed. Furthermore, if the fleet in the
            Black Sea gets a second order, then this may fail, because of double orders (although it can also be ruled
            differently, see issue 4.D.3). However, when the support order is considered "illegal" (see issue 4.E.1),
            then this impossible support must be ignored and the second order must be carried out.
            I prefer that impossible orders are "illegal" and ignored. If there would be a second order for the fleet
            in the Black Sea, that order should be carried out.
        """
        b = BoardBuilder()
        a_rumania = b.move(b.austria, UnitType.ARMY, b.rumania, b.armenia)
        f_black_sea = b.supportMove(b.turkey, UnitType.FLEET, b.black_sea, a_rumania, b.armenia)

        b.assertIllegal(a_rumania, f_black_sea)
        b.moves_adjudicate(self)

    def test_6_d_32(self):
        """ 6.D.32. TEST CASE, A MISSING FLEET
            The previous test cases contained an order that was impossible even when some other pieces on the board
            where changed. In this test case, the order is impossible, but only for that situation.
            England: F Edinburgh Supports A Liverpool - Yorkshire
            England: A Liverpool - Yorkshire
            France: F London Supports A Yorkshire
            Germany: A Yorkshire - Holland
            The German order to Yorkshire can not be executed, because there is no fleet in the North Sea. In other
            situations (where there is a fleet in the North Sea), the exact same order would be possible. It should be
            determined whether this is "illegal" (see issue 4.E.1) or not. If it is illegal, then the order should be
            ignored and the support of the French fleet in London succeeds. This means that the army in Yorkshire is
            not dislodged.
            I prefer that impossible yorkshireorders, even if it is only impossible for the current situation, are "illegal" and
            ignored. The army in Yorkshire is not dislodged.
        """
        b = BoardBuilder()
        a_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.yorkshire)
        f_edinburgh = b.supportMove(b.england, UnitType.FLEET, b.edinburgh_c, a_liverpool, b.yorkshire)
        a_yorkshire = b.move(b.germany, UnitType.ARMY, b.yorkshire, b.holland)
        f_london = b.supportHold(b.france, UnitType.FLEET, b.london_c, a_yorkshire)

        b.assertNotDislodge(a_yorkshire)
        b.assertIllegal(a_yorkshire)
        b.assertSuccess(f_edinburgh, f_london)
        b.assertFail(a_liverpool)
        b.moves_adjudicate(self)

    def test_6_d_33(self):
        """ 6.D.33. TEST CASE, UNWANTED SUPPORT ALLOWED
            A self stand-off can be broken by an unwanted support.
            Austria: A Serbia - Budapest
            Austria: A Vienna - Budapest
            Russia: A Galicia Supports A Serbia - Budapest
            Turkey: A Bulgaria - Serbia
            Due to the Russian support, the army in Serbia advances to Budapest. This enables Turkey to capture
            Serbia with the army in Bulgaria.
        """
        b = BoardBuilder()
        a_serbia = b.move(b.austria, UnitType.ARMY, b.serbia, b.budapest)
        a_vienna = b.move(b.austria, UnitType.ARMY, b.vienna, b.budapest)
        a_galicia = b.supportMove(b.russia, UnitType.ARMY, b.galicia, a_serbia, b.budapest)
        a_bulgaria = b.move(b.turkey, UnitType.ARMY, b.bulgaria, b.serbia)

        b.assertSuccess(a_serbia, a_bulgaria)
        b.assertFail(a_vienna)
        b.moves_adjudicate(self)

    def test_6_d_34(self):
        """ 6.D.34. TEST CASE, SUPPORT TARGETING OWN AREA NOT ALLOWED
            Support targeting the area where the supporting unit is standing, is illegal.
            Germany: A Berlin - Prussia
            Germany: A Silesia Supports A Berlin - Prussia
            Germany: F Baltic Sea Supports A Berlin - Prussia
            Italy: A Prussia Supports Livonia - Prussia
            Russia: A Warsaw Supports A Livonia - Prussia
            Russia: A Livonia - Prussia
            Russia and Italy wanted to get rid of the Italian army in Prussia (to build an Italian fleet somewhere
            else). However, they didn't want a possible German attack on Prussia to succeed. They invented this odd
            order of Italy. It was intended that the attack of the army in Livonia would have strength three, so it
            would be capable to prevent the possible German attack to succeed. However, the order of Italy is illegal,
            because a unit may only support to an area where the unit can go by itself. A unit can't go to the area it
            is already standing, so the Italian order is illegal and the German move from Berlin succeeds. Even if it
            would be legal, the German move from Berlin would still succeed, because the support of Prussia is cut by
            Livonia and Berlin.
        """
        b = BoardBuilder()
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.prussia)
        a_silesia = b.supportMove(b.germany, UnitType.ARMY, b.silesia, a_berlin, b.prussia)
        f_baltic_sea = b.supportMove(b.germany, UnitType.FLEET, b.baltic_sea, a_berlin, b.prussia)
        a_prussia = b.supportMove(b.italy, UnitType.ARMY, b.prussia, a_berlin, b.prussia) # illegal
        a_livonia = b.move(b.russia, UnitType.ARMY, b.livonia, b.prussia)
        a_warsaw = b.supportMove(b.russia, UnitType.ARMY, b.warsaw, a_livonia, b.prussia)

        b.assertIllegal(a_prussia)
        b.assertSuccess(a_berlin, a_silesia, f_baltic_sea, a_warsaw)
        b.assertFail(a_livonia)
        b.assertDislodge(a_prussia)
        b.moves_adjudicate(self)

    def test_6_e_1(self):
        """ 6.E.1. TEST CASE, DISLODGED UNIT HAS NO EFFECT ON ATTACKERS AREA
            An army can follow.
            Germany: A Berlin - Prussia
            Germany: F Kiel - Berlin
            Germany: A Silesia Supports A Berlin - Prussia
            Russia: A Prussia - Berlin
            The army in Kiel will move to Berlin.
        """
        b = BoardBuilder()
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.prussia)
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.berlin)
        a_silesia = b.supportMove(b.germany, UnitType.ARMY, b.silesia, a_berlin, b.prussia)
        a_prussia = b.move(b.russia, UnitType.ARMY, b.prussia, b.berlin)

        b.assertSuccess(f_kiel, a_berlin, a_silesia)
        b.assertFail(a_prussia)
        b.moves_adjudicate(self)

    def test_6_e_2(self):
        """ 6.E.2. TEST CASE, NO SELF DISLODGEMENT IN HEAD TO HEAD BATTLE
            Self dislodgement is not allowed. This also counts for head to head battles.
            Germany: A Berlin - Kiel
            Germany: F Kiel - Berlin
            Germany: A Munich Supports A Berlin - Kiel
            No unit will move.
        """
        b = BoardBuilder()
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.kiel)
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.berlin_c)
        a_munich = b.supportMove(b.germany, UnitType.ARMY, b.munich, a_berlin, b.kiel)

        b.assertFail(a_berlin, f_kiel)
        b.assertSuccess(a_munich)
        b.moves_adjudicate(self)

    def test_6_e_3(self):
        """ 6.E.3. TEST CASE, NO HELP IN DISLODGING OWN UNIT
            To help a foreign power to dislodge own unit in head to head battle is not possible.
            Germany: A Berlin - Kiel
            Germany: A Munich Supports F Kiel - Berlin
            England: F Kiel - Berlin
            No unit will move.
        """
        b = BoardBuilder()
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.kiel)
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.berlin_c)
        a_munich = b.supportMove(b.germany, UnitType.ARMY, b.munich, f_kiel, b.berlin)

        b.assertFail(a_berlin, f_kiel)
        b.assertSuccess(a_munich)
        b.moves_adjudicate(self)

    def test_6_e_4(self):
        """ 6.E.4. TEST CASE, NON-DISLODGED LOSER HAS STILL EFFECT
            If in an unbalanced head to head battle the loser is not dislodged, it has still effect on the area of
            the attacker.
            Germany: F Holland - North Sea
            Germany: F Helgoland Bight Supports F Holland - North Sea
            Germany: F Skagerrak Supports F Holland - North Sea
            France: F North Sea - Holland
            France: F Belgium Supports F North Sea - Holland
            England: F Edinburgh Supports F Norwegian Sea - North Sea
            England: F Yorkshire Supports F Norwegian Sea - North Sea
            England: F Norwegian Sea - North Sea
            Austria: A Kiel Supports A Ruhr - Holland
            Austria: A Ruhr - Holland
            The French fleet in the North Sea is not dislodged due to the beleaguered garrison. Therefore,
            the Austrian army in Ruhr will not move to Holland.
        """
        b = BoardBuilder()
        f_holland = b.move(b.germany, UnitType.FLEET, b.holland_c, b.north_sea)
        f_helgoland_bight = b.supportMove(b.germany, UnitType.FLEET, b.helgoland_bight, f_holland, b.north_sea)
        f_skagerrak = b.supportMove(b.germany, UnitType.FLEET, b.skagerrak, f_holland, b.north_sea)
        f_north_sea = b.move(b.france, UnitType.FLEET, b.north_sea, b.holland_c)
        f_belgium = b.supportMove(b.france, UnitType.FLEET, b.belgium_c, f_north_sea, b.holland_c)
        f_norwegian_sea = b.move(b.england, UnitType.FLEET, b.norwegian_sea, b.north_sea)
        f_edinburgh = b.supportMove(b.england, UnitType.FLEET, b.edinburgh_c, f_norwegian_sea, b.north_sea)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, f_norwegian_sea, b.north_sea)
        a_ruhr = b.move(b.austria, UnitType.ARMY, b.ruhr, b.holland)
        a_kiel = b.supportMove(b.austria, UnitType.ARMY, b.kiel, a_ruhr, b.holland)

        b.assertSuccess(f_helgoland_bight, f_skagerrak, f_edinburgh, f_yorkshire, a_kiel, f_belgium)
        b.assertFail(f_holland, f_norwegian_sea, f_north_sea, a_ruhr)
        b.assertNotDislodge(f_holland, f_north_sea)
        b.moves_adjudicate(self)

    def test_6_e_5(self):
        """ 6.E.5. TEST CASE, LOSER DISLODGED BY ANOTHER ARMY HAS STILL EFFECT
            If in an unbalanced head to head battle the loser is dislodged by a unit not part of the head to head
            battle, the loser has still effect on the place of the winner of the head to head battle.
            Germany: F Holland - North Sea
            Germany: F Helgoland Bight Supports F Holland - North Sea
            Germany: F Skagerrak Supports F Holland - North Sea
            France: F North Sea - Holland
            France: F Belgium Supports F North Sea - Holland
            England: F Edinburgh Supports F Norwegian Sea - North Sea
            England: F Yorkshire Supports F Norwegian Sea - North Sea
            England: F Norwegian Sea - North Sea
            England: F London Supports F Norwegian Sea - North Sea
            Austria: A Kiel Supports A Ruhr - Holland
            Austria: A Ruhr - Holland
            The French fleet in the North Sea is dislodged but not by the German fleet in Holland. Therefore,
            the French fleet can still prevent that the Austrian army in Ruhr will move to Holland. So, the Austrian
            move in Ruhr fails and the German fleet in Holland is not dislodged.
        """
        b = BoardBuilder()
        f_holland = b.move(b.germany, UnitType.FLEET, b.holland_c, b.north_sea)
        f_helgoland_bight = b.supportMove(b.germany, UnitType.FLEET, b.helgoland_bight, f_holland, b.north_sea)
        f_skagerrak = b.supportMove(b.germany, UnitType.FLEET, b.skagerrak, f_holland, b.north_sea)
        f_north_sea = b.move(b.france, UnitType.FLEET, b.north_sea, b.holland_c)
        f_belgium = b.supportMove(b.france, UnitType.FLEET, b.belgium_c, f_north_sea, b.holland_c)
        f_norwegian_sea = b.move(b.england, UnitType.FLEET, b.norwegian_sea, b.north_sea)
        f_edinburgh = b.supportMove(b.england, UnitType.FLEET, b.edinburgh_c, f_norwegian_sea, b.north_sea)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, f_norwegian_sea, b.north_sea)
        f_london = b.supportMove(b.england, UnitType.FLEET, b.london_c, f_norwegian_sea, b.north_sea)
        a_ruhr = b.move(b.austria, UnitType.ARMY, b.ruhr, b.holland)
        a_kiel = b.supportMove(b.austria, UnitType.ARMY, b.kiel, a_ruhr, b.holland)

        b.assertSuccess(f_helgoland_bight, f_skagerrak, f_edinburgh, f_yorkshire, a_kiel, f_belgium, f_london, f_norwegian_sea)
        b.assertFail(f_holland, f_north_sea, a_ruhr)
        b.assertNotDislodge(f_holland)
        b.assertDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_e_6(self):
        """ 6.E.6. TEST CASE, NOT DISLODGE BECAUSE OF OWN SUPPORT HAS STILL EFFECT
            If in an unbalanced head to head battle the loser is not dislodged because the winner had help of a unit
            of the loser, the loser has still effect on the area of the winner.
            Germany: F Holland - North Sea
            Germany: F Helgoland Bight Supports F Holland - North Sea
            France: F North Sea - Holland
            France: F Belgium Supports F North Sea - Holland
            France: F English Channel Supports F Holland - North Sea
            Austria: A Kiel Supports A Ruhr - Holland
            Austria: A Ruhr - Holland
            Although the German force from Holland to North Sea is one larger than the French force from North Sea
            to Holland,
            the French fleet in the North Sea is not dislodged, because one of the supports on the German movement is
            French.
            Therefore, the Austrian army in Ruhr will not move to Holland.
        """
        b = BoardBuilder()
        f_holland = b.move(b.germany, UnitType.FLEET, b.holland_c, b.north_sea)
        f_helgoland_bight = b.supportMove(b.germany, UnitType.FLEET, b.helgoland_bight, f_holland, b.north_sea)
        f_north_sea = b.move(b.france, UnitType.FLEET, b.north_sea, b.holland_c)
        f_belgium = b.supportMove(b.france, UnitType.FLEET, b.belgium_c, f_north_sea, b.holland_c)
        f_english_channel = b.supportMove(b.france, UnitType.FLEET, b.english_channel, f_holland, b.north_sea)
        a_ruhr = b.move(b.austria, UnitType.ARMY, b.ruhr, b.holland)
        a_kiel = b.supportMove(b.austria, UnitType.ARMY, b.kiel, a_ruhr, b.holland)

        b.assertSuccess(f_helgoland_bight, a_kiel, f_belgium)
        b.assertFail(f_holland, f_north_sea, a_ruhr)
        b.assertNotDislodge(f_holland, f_north_sea)
        b.moves_adjudicate(self)

    def test_6_e_7(self):
        """ 6.E.7. TEST CASE, NO SELF DISLODGEMENT WITH BELEAGUERED GARRISON
            An attempt to self dislodgement can be combined with a beleaguered garrison. Such self dislodgment is still
            not possible.
            England: F North Sea Hold
            England: F Yorkshire Supports F Norway - North Sea
            Germany: F Holland Supports F Helgoland Bight - North Sea
            Germany: F Helgoland Bight - North Sea
            Russia: F Skagerrak Supports F Norway - North Sea
            Russia: F Norway - North Sea
            Although the Russians beat the German attack (with the support of Yorkshire) and the two Russian fleets
            are enough to dislodge the fleet in the North Sea, the fleet in the North Sea is not dislodged, since it
            would not be dislodged if the English fleet in Yorkshire would not give support. According to the DPTG the
            fleet in the North Sea would be dislodged. The DPTG is incorrect in this case.
        """
        b = BoardBuilder()
        f_north_sea = b.hold(b.england, UnitType.FLEET, b.north_sea)
        f_helgoland_bight = b.move(b.germany, UnitType.FLEET, b.helgoland_bight, b.north_sea)
        f_holland = b.supportMove(b.germany, UnitType.FLEET, b.holland_c, f_helgoland_bight, b.north_sea)
        f_norway = b.move(b.russia, UnitType.FLEET, b.norway_c, b.north_sea)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, f_norway, b.north_sea)
        f_skagerrak = b.supportMove(b.russia, UnitType.FLEET, b.skagerrak, f_norway, b.north_sea)

        b.assertSuccess(f_holland, f_yorkshire, f_skagerrak)
        b.assertFail(f_norway, f_helgoland_bight)
        b.assertNotDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_e_8(self):
        """ 6.E.8. TEST CASE, NO SELF DISLODGEMENT WITH BELEAGUERED GARRISON AND HEAD TO HEAD BATTLE
            Similar to the previous test case, but now the beleaguered fleet is also engaged in a head to head battle.
            England: F North Sea - Norway
            England: F Yorkshire Supports F Norway - North Sea
            Germany: F Holland Supports F Helgoland Bight - North Sea
            Germany: F Helgoland Bight - North Sea
            Russia: F Skagerrak Supports F Norway - North Sea
            Russia: F Norway - North Sea
            Again, none of the fleets move.
        """
        b = BoardBuilder()
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.norway_c)
        f_helgoland_bight = b.move(b.germany, UnitType.FLEET, b.helgoland_bight, b.north_sea)
        f_holland = b.supportMove(b.germany, UnitType.FLEET, b.holland_c, f_helgoland_bight, b.north_sea)
        f_norway = b.move(b.russia, UnitType.FLEET, b.norway_c, b.north_sea)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, f_norway, b.north_sea)
        f_skagerrak = b.supportMove(b.russia, UnitType.FLEET, b.skagerrak, f_norway, b.north_sea)

        b.assertSuccess(f_holland, f_yorkshire, f_skagerrak)
        b.assertFail(f_norway, f_helgoland_bight, f_north_sea)
        b.assertNotDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_e_9(self):
        """ 6.E.9. TEST CASE, ALMOST SELF DISLODGEMENT WITH BELEAGUERED GARRISON
            Similar to the previous test case, but now the beleaguered fleet is moving away.
            England: F North Sea - Norwegian Sea
            England: F Yorkshire Supports F Norway - North Sea
            Germany: F Holland Supports F Helgoland Bight - North Sea
            Germany: F Helgoland Bight - North Sea
            Russia: F Skagerrak Supports F Norway - North Sea
            Russia: F Norway - North Sea
            Both the fleet in the North Sea and the fleet in Norway move.
        """
        b = BoardBuilder()
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.norwegian_sea)
        f_helgoland_bight = b.move(b.germany, UnitType.FLEET, b.helgoland_bight, b.north_sea)
        f_holland = b.supportMove(b.germany, UnitType.FLEET, b.holland_c, f_helgoland_bight, b.north_sea)
        f_norway = b.move(b.russia, UnitType.FLEET, b.norway_c, b.north_sea)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, f_norway, b.north_sea)
        f_skagerrak = b.supportMove(b.russia, UnitType.FLEET, b.skagerrak, f_norway, b.north_sea)

        b.assertSuccess(f_holland, f_yorkshire, f_skagerrak, f_north_sea)
        b.assertFail(f_helgoland_bight, f_norway)
        b.assertNotDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_e_10(self):
        """ 6.E.10. TEST CASE, ALMOST CIRCULAR MOVEMENT WITH NO SELF DISLODGEMENT WITH BELEAGUERED GARRISON
            Similar to the previous test case, but now the beleaguered fleet is in circular movement with the weaker
            attacker. So, the circular movement fails.
            England: F North Sea - Denmark
            England: F Yorkshire Supports F Norway - North Sea
            Germany: F Holland Supports F Helgoland Bight - North Sea
            Germany: F Helgoland Bight - North Sea
            Germany: F Denmark - Helgoland Bight
            Russia: F Skagerrak Supports F Norway - North Sea
            Russia: F Norway - North Sea
            There is no movement of fleets.
        """
        b = BoardBuilder()
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.denmark_c)
        f_helgoland_bight = b.move(b.germany, UnitType.FLEET, b.helgoland_bight, b.north_sea)
        f_holland = b.supportMove(b.germany, UnitType.FLEET, b.holland_c, f_helgoland_bight, b.north_sea)
        f_norway = b.move(b.russia, UnitType.FLEET, b.norway_c, b.north_sea)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, f_norway, b.north_sea)
        f_skagerrak = b.supportMove(b.russia, UnitType.FLEET, b.skagerrak, f_norway, b.north_sea)
        f_denmark = b.move(b.germany, UnitType.FLEET, b.denmark_c, b.helgoland_bight)

        b.assertSuccess(f_holland, f_yorkshire, f_skagerrak)
        b.assertFail(f_helgoland_bight, f_north_sea, f_denmark, f_norway)
        b.assertNotDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_e_11(self):
        """ 6.E.11. TEST CASE, NO SELF DISLODGEMENT WITH BELEAGUERED GARRISON, UNIT SWAP WITH ADJACENT CONVOYING AND
            TWO COASTS
            Similar to the previous test case, but now the beleaguered fleet is in a unit swap with the stronger
            attacker. So, the unit swap succeeds. To make the situation more complex, the swap is on an area with
            two coasts.
            France: A Spain - Portugal via Convoy
            France: F Mid-Atlantic Ocean Convoys A Spain - Portugal
            France: F Gulf of Lyon Supports F Portugal - Spain(nc)
            Germany: A Marseilles Supports A Gascony - Spain
            Germany: A Gascony - Spain
            Italy: F Portugal - Spain(nc)
            Italy: F Western Mediterranean Supports F Portugal - Spain(nc)
            The unit swap succeeds. Note that due to the success of the swap, there is no beleaguered garrison anymore.
        """
        b = BoardBuilder()
        a_spain = b.move(b.france, UnitType.ARMY, b.spain, b.portugal)
        f_portugal = b.move(b.italy, UnitType.FLEET, b.portugal_c, b.spain_nc)
        f_western_mediterranean = b.supportMove(b.italy, UnitType.FLEET, b.western_mediterranean, f_portugal, b.spain_nc)
        f_mid_atlantic_ocean = b.convoy(b.france, b.mid_atlantic_ocean, a_spain, b.portugal)
        f_gulf_of_lyon = b.supportMove(b.france, UnitType.FLEET, b.gulf_of_lyon, f_portugal, b.spain_nc)
        a_gascony = b.move(b.germany, UnitType.ARMY, b.gascony, b.spain)
        a_marseilles = b.supportMove(b.germany, UnitType.ARMY, b.marseilles, a_gascony, b.spain)

        b.assertSuccess(a_spain, f_portugal, f_western_mediterranean, f_gulf_of_lyon, f_mid_atlantic_ocean, a_marseilles)
        b.assertFail(a_gascony)
        b.moves_adjudicate(self)

    def test_6_e_12(self):
        """ 6.E.12. TEST CASE, SUPPORT ON ATTACK ON OWN UNIT CAN BE USED FOR OTHER MEANS
            A support on an attack on your own unit has still effect. It can prevent that another army will dislodge
            the unit.
            Austria: A Budapest - Rumania
            Austria: A Serbia Supports A Vienna - Budapest
            Italy: A Vienna - Budapest
            Russia: A Galicia - Budapest
            Russia: A Rumania Supports A Galicia - Budapest
            The support of Serbia on the Italian army prevents that the Russian army in Galicia will advance.
            No army will move.
        """
        b = BoardBuilder()
        a_budapest = b.move(b.austria, UnitType.ARMY, b.budapest, b.rumania)
        a_vienna = b.move(b.italy, UnitType.ARMY, b.vienna, b.budapest)
        a_serbia = b.supportMove(b.austria, UnitType.ARMY, b.serbia, a_vienna, b.budapest)
        a_galicia = b.move(b.russia, UnitType.ARMY, b.galicia, b.budapest)
        a_rumania = b.supportMove(b.russia, UnitType.ARMY, b.rumania, a_galicia, b.budapest)

        b.assertFail(a_galicia, a_vienna, a_budapest)
        b.assertSuccess(a_serbia, a_rumania)
        b.assertNotDislodge(a_budapest)
        b.moves_adjudicate(self)

    def test_6_e_13(self):
        """ 6.E.13. TEST CASE, THREE WAY BELEAGUERED GARRISON
            In a beleaguered garrison from three sides, the adjudicator may not let two attacks fail and then let the
            third succeed.
            England: F Edinburgh Supports F Yorkshire - North Sea
            England: F Yorkshire - North Sea
            France: F Belgium - North Sea
            France: F English Channel Supports F Belgium - North Sea
            Germany: F North Sea Hold
            Russia: F Norwegian Sea - North Sea
            Russia: F Norway Supports F Norwegian Sea - North Sea
            None of the fleets move. The German fleet in the North Sea is not dislodged.
        """
        b = BoardBuilder()
        f_yorkshire = b.move(b.england, UnitType.FLEET, b.yorkshire_c, b.north_sea)
        f_edinburgh = b.supportMove(b.england, UnitType.FLEET, b.edinburgh_c, f_yorkshire, b.north_sea)
        f_belgium = b.move(b.france, UnitType.FLEET, b.belgium_c, b.north_sea)
        f_english_channel = b.supportMove(b.france, UnitType.FLEET, b.english_channel, f_belgium, b.north_sea)
        f_north_sea = b.hold(b.germany, UnitType.FLEET, b.north_sea)
        f_norwegian_sea = b.move(b.russia, UnitType.FLEET, b.norwegian_sea, b.north_sea)
        f_norway = b.supportMove(b.russia, UnitType.FLEET, b.norway_c, f_norwegian_sea, b.north_sea)

        b.assertSuccess(f_edinburgh, f_english_channel, f_norway)
        b.assertFail(f_yorkshire, f_belgium, f_norwegian_sea)
        b.assertNotDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_e_14(self):
        """ 6.E.14. TEST CASE, ILLEGAL HEAD TO HEAD BATTLE CAN STILL DEFEND
            If in a head to head battle, one of the units makes an illegal move, than that unit has still the
            possibility to defend against attacks with strength of one.
            England: A Liverpool - Edinburgh
            Russia: F Edinburgh - Liverpool
            The move of the Russian fleet is illegal, but can still prevent the English army to enter Edinburgh. So,
            none of the units move.
        """
        b = BoardBuilder()
        a_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.edinburgh)
        f_edinburgh = b.move(b.russia, UnitType.FLEET, b.edinburgh_c, b.liverpool_c)

        b.assertIllegal(f_edinburgh)
        b.assertFail(a_liverpool)
        b.moves_adjudicate(self)

    def test_6_e_15(self):
        """ 6.E.15. TEST CASE, THE FRIENDLY HEAD TO HEAD BATTLE
            In this case both units in the head to head battle prevent that the other one is dislodged.
            England: F Holland Supports A Ruhr - Kiel
            England: A Ruhr - Kiel
            France: A Kiel - Berlin
            France: A Munich Supports A Kiel - Berlin
            France: A Silesia Supports A Kiel - Berlin
            Germany: A Berlin - Kiel
            Germany: F Denmark Supports A Berlin - Kiel
            Germany: F Helgoland Bight Supports A Berlin - Kiel
            Russia: F Baltic Sea Supports A Prussia - Berlin
            Russia: A Prussia - Berlin
            None of the moves succeeds. This case is especially difficult for sequence based adjudicators. They will
            start adjudicating the head to head battle and continue to adjudicate the attack on one of the units part
            of the head to head battle. In this self.process, one of the sides of the head to head battle might be
            cancelled out. This happens in the DPTG. If this is adjudicated according to the DPTG, the unit in Ruhr or
            in Prussia will advance (depending on the order the units are adjudicated). This is clearly a bug in the
            DPTG.
        """
        b = BoardBuilder()
        a_ruhr = b.move(b.england, UnitType.ARMY, b.ruhr, b.kiel)
        f_holland = b.supportMove(b.england, UnitType.FLEET, b.holland_c, a_ruhr, b.kiel)
        a_kiel = b.move(b.france, UnitType.ARMY, b.kiel, b.berlin)
        a_munich = b.supportMove(b.france, UnitType.ARMY, b.munich, a_kiel, b.berlin)
        a_silesia = b.supportMove(b.france, UnitType.ARMY, b.silesia, a_kiel, b.berlin)
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.kiel)
        f_denmark = b.supportMove(b.germany, UnitType.FLEET, b.denmark_c, a_berlin, b.kiel)
        f_helgoland_bight = b.supportMove(b.germany, UnitType.FLEET, b.helgoland_bight, a_berlin, b.kiel)
        a_prussia = b.move(b.russia, UnitType.ARMY, b.prussia, b.berlin)
        f_baltic_sea = b.supportMove(b.russia, UnitType.FLEET, b.baltic_sea, a_prussia, b.berlin)

        b.assertSuccess(f_holland, a_munich, a_silesia, f_denmark, f_helgoland_bight, f_baltic_sea)
        b.assertFail(a_ruhr, a_kiel, a_berlin, a_prussia)
        b.moves_adjudicate(self)

    def test_6_f_1(self):
        """ 6.F.1. TEST CASE, NO CONVOY IN COASTAL AREAS
            A fleet in a coastal area may not convoy.
            Turkey: A Greece - Sevastopol
            Turkey: F Aegean Sea Convoys A Greece - Sevastopol
            Turkey: F Constantinople Convoys A Greece - Sevastopol
            Turkey: F Black Sea Convoys A Greece - Sevastopol
            The convoy in Constantinople is not possible. So, the army in Greece will not move to Sevastopol.
        """
        b = BoardBuilder()
        a_greece = b.move(b.turkey, UnitType.ARMY, b.greece, b.sevastopol)
        f_aegean_sea = b.convoy(b.turkey, b.aegean_sea, a_greece, b.sevastopol)
        f_constantinople = b.convoy(b.turkey, b.constantinople_c, a_greece, b.sevastopol)
        f_black_sea = b.convoy(b.turkey, b.black_sea, a_greece, b.sevastopol)

        b.assertIllegal(f_constantinople, a_greece, f_aegean_sea, f_black_sea)
        b.moves_adjudicate(self)

    def test_6_f_2(self):
        """ 6.F.2. TEST CASE, AN ARMY BEING CONVOYED CAN BOUNCE AS NORMAL
            Armies being convoyed bounce on other units just as armies that are not being convoyed.
            England: F English Channel Convoys A London - Brest
            England: A London - Brest
            France: A Paris - Brest
            The English army in London bounces on the French army in Paris. Both units do not move.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.brest)
        f_english_channel = b.convoy(b.england, b.english_channel, a_london, b.brest)
        a_paris = b.move(b.france, UnitType.ARMY, b.paris, b.brest)

        b.assertFail(a_london, a_paris)
        b.moves_adjudicate(self)

    def test_6_f_3(self):
        """ 6.F.3. TEST CASE, AN ARMY BEING CONVOYED CAN RECEIVE SUPPORT
            Armies being convoyed can receive support as in any other move.
            England: F English Channel Convoys A London - Brest
            England: A London - Brest
            England: F Mid-Atlantic Ocean Supports A London - Brest
            France: A Paris - Brest
            The army in London receives support and beats the army in Paris. This means that the army London will end
            in Brest and the French army in Paris stays in Paris.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.brest)
        f_english_channel = b.convoy(b.england, b.english_channel, a_london, b.brest)
        a_mid_atlantic_ocean = b.supportMove(b.england, UnitType.FLEET, b.mid_atlantic_ocean, a_london, b.brest)
        a_paris = b.move(b.france, UnitType.ARMY, b.paris, b.brest)

        b.assertFail(a_paris)
        b.assertSuccess(a_london)
        b.moves_adjudicate(self)

    def test_6_f_4(self):
        """ 6.F.4. TEST CASE, AN ATTACKED CONVOY IS NOT DISRUPTED
            A convoy can only be disrupted by dislodging the fleets. Attacking is not sufficient.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            Germany: F Skagerrak - North Sea
            The army in London will successfully convoy and end in Holland.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.holland)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.holland)
        f_skagerrak = b.move(b.germany, UnitType.FLEET, b.skagerrak, b.north_sea)

        b.assertSuccess(a_london, f_north_sea)
        b.moves_adjudicate(self)

    def test_6_f_5(self):
        """ 6.F.5. TEST CASE, A BELEAGUERED CONVOY IS NOT DISRUPTED
            Even when a convoy is in a beleaguered garrison it is not disrupted.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            France: F English Channel - North Sea
            France: F Belgium Supports F English Channel - North Sea
            Germany: F Skagerrak - North Sea
            Germany: F Denmark Supports F Skagerrak - North Sea
            The army in London will successfully convoy and end in Holland.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.holland)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.holland)
        f_english_channel = b.move(b.france, UnitType.FLEET, b.english_channel, b.north_sea)
        f_belgium = b.supportMove(b.france, UnitType.FLEET, b.belgium_c, f_english_channel, b.north_sea)        
        f_skagerrak = b.move(b.germany, UnitType.FLEET, b.skagerrak, b.north_sea)
        f_denmark = b.supportMove(b.germany, UnitType.FLEET, b.denmark_c, f_skagerrak, b.north_sea)

        b.assertSuccess(a_london, f_north_sea)
        b.assertFail(f_english_channel, f_skagerrak)
        b.assertNotDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_f_6(self):
        """ 6.F.6. TEST CASE, DISLODGED CONVOY DOES NOT CUT SUPPORT
            When a fleet of a convoy is dislodged, the convoy is completely cancelled. So, no support is cut.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            Germany: A Holland Supports A Belgium
            Germany: A Belgium Supports A Holland
            Germany: F Helgoland Bight Supports F Skagerrak - North Sea
            Germany: F Skagerrak - North Sea
            France: A Picardy - Belgium
            France: A Burgundy Supports A Picardy - Belgium
            The hold order of Holland on Belgium will sustain and Belgium will not be dislodged by the French in
            Picardy.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.holland)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.holland)
        a_holland = b.army(b.holland, b.germany)
        a_belgium = b.army(b.belgium, b.germany)
        a_holland.order = Support(a_belgium, b.belgium)
        a_belgium.order = Support(a_holland, b.holland)
        f_skagerrak = b.move(b.germany, UnitType.FLEET, b.skagerrak, b.north_sea)
        f_helgoland_bight = b.supportMove(b.germany, UnitType.FLEET, b.helgoland_bight, f_skagerrak, b.north_sea)
        a_picardy = b.move(b.france, UnitType.ARMY, b.picardy, b.belgium)
        a_burgundy = b.supportMove(b.france, UnitType.ARMY, b.picardy, a_picardy, b.belgium)

        b.assertSuccess(a_holland, f_helgoland_bight, a_burgundy)
        b.assertFail(a_picardy, a_london, f_north_sea, a_belgium)
        b.assertNotDislodge(a_holland)
        b.assertDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_f_7(self):
        """ 6.F.7. TEST CASE, DISLODGED CONVOY DOES NOT CAUSE CONTESTED AREA
            When a fleet of a convoy is dislodged, the landing area is not contested, so other units can retreat to
            that area.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            Germany: F Helgoland Bight Supports F Skagerrak - North Sea
            Germany: F Skagerrak - North Sea
            The dislodged English fleet can retreat to Holland.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.holland)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.holland)
        f_skagerrak = b.move(b.germany, UnitType.FLEET, b.skagerrak, b.north_sea)
        f_helgoland_bight = b.supportMove(b.germany, UnitType.FLEET, b.helgoland_bight, f_skagerrak, b.north_sea)

        b.assertFail(a_london, f_north_sea)
        b.assertDislodge(f_north_sea)
        b.moves_adjudicate(self)
        self.assertTrue(b.holland in f_north_sea.retreat_options, "Holland not in North Sea Retreat Options")

    def test_6_f_8(self):
        """ 6.F.8. TEST CASE, DISLODGED CONVOY DOES NOT CAUSE A BOUNCE
            When a fleet of a convoy is dislodged, then there will be no bounce in the landing area.
            England: F North Sea Convoys A London - Holland
            England: A London - Holland
            Germany: F Helgoland Bight Supports F Skagerrak - North Sea
            Germany: F Skagerrak - North Sea
            Germany: A Belgium - Holland
            The army in Belgium will not bounce and move to Holland.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.holland)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.holland)
        f_skagerrak = b.move(b.germany, UnitType.FLEET, b.skagerrak, b.north_sea)
        f_helgoland_bight = b.supportMove(b.germany, UnitType.FLEET, b.helgoland_bight, f_skagerrak, b.north_sea)
        a_belgium = b.move(b.germany, UnitType.ARMY, b.belgium, b.holland)

        b.assertFail(a_london, f_north_sea)
        b.assertDislodge(f_north_sea)
        b.assertSuccess(a_belgium)
        b.moves_adjudicate(self)

    def test_6_f_9(self):
        """ 6.F.9. TEST CASE, DISLODGE OF MULTI-ROUTE CONVOY
            When a fleet of a convoy with multiple routes is dislodged, the result depends on the rulebook that is used.
            England: F English Channel Convoys A London - Belgium
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            France: F Brest Supports F Mid-Atlantic Ocean - English Channel
            France: F Mid-Atlantic Ocean - English Channel
            The French fleet in Mid Atlantic Ocean will dislodge the convoying fleet in the English Channel. If the
            1971 rules are used (see issue 4.A.1), this will disrupt the convoy and the army will stay in London. When
            the 1982 or 2000 rulebook is used (which I prefer) the army can still go via the North Sea and the convoy
            succeeds and the London army will end in Belgium.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.belgium)
        f_english_channel = b.convoy(b.england, b.english_channel, a_london, b.belgium)
        f_mid_atlantic_ocean = b.move(b.france, UnitType.FLEET, b.mid_atlantic_ocean, b.english_channel)
        f_brest = b.supportMove(b.france, UnitType.FLEET, b.brest_c, f_mid_atlantic_ocean, b.english_channel)

        b.assertSuccess(a_london)
        b.assertFail(f_english_channel)
        b.assertDislodge(f_english_channel)
        b.moves_adjudicate(self)

    def test_6_f_10(self):
        """ 6.F.10. TEST CASE, DISLODGE OF MULTI-ROUTE CONVOY WITH FOREIGN FLEET
            When the 1971 rulebook is used "unwanted" multi-route convoys are possible.
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            Germany: F English Channel Convoys A London - Belgium
            France: F Brest Supports F Mid-Atlantic Ocean - English Channel
            France: F Mid-Atlantic Ocean - English Channel
            If the 1982 or 2000 rulebook is used (which I prefer), it makes no difference that the convoying fleet in
            the English Channel is German. It will take the convoy via the North Sea anyway and the army in London will
            end in Belgium. However, when the 1971 rules are used, the German convoy is "unwanted". According to the
            DPTG the German fleet should be ignored in the English convoy, since there is a convoy path with only
            English fleets. That means that the convoy is not disrupted and the English army in London will end in
            Belgium. See also issue 4.A.1.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.belgium)
        f_english_channel = b.convoy(b.germany, b.english_channel, a_london, b.belgium)
        f_mid_atlantic_ocean = b.move(b.france, UnitType.FLEET, b.mid_atlantic_ocean, b.english_channel)
        f_brest = b.supportMove(b.france, UnitType.FLEET, b.brest_c, f_mid_atlantic_ocean, b.english_channel)

        b.assertSuccess(a_london)
        b.assertFail(f_english_channel)
        b.assertDislodge(f_english_channel)
        b.moves_adjudicate(self)

    def test_6_f_11(self):
        """ 6.F.11. TEST CASE, DISLODGE OF MULTI-ROUTE CONVOY WITH ONLY FOREIGN FLEETS
            When the 1971 rulebook is used, "unwanted" convoys can not be ignored in all cases.
            England: A London - Belgium
            Germany: F English Channel Convoys A London - Belgium
            Russia: F North Sea Convoys A London - Belgium
            France: F Brest Supports F Mid-Atlantic Ocean - English Channel
            France: F Mid-Atlantic Ocean - English Channel
            If the 1982 or 2000 rulebook is used (which I prefer), it makes no difference that the convoying fleets
            are not English. It will take the convoy via the North Sea anyway and the army in London will end in
            Belgium. However, when the 1971 rules are used, the situation is different. Since both the fleet in the
            English Channel as the fleet in North Sea are not English, it can not be concluded that the German fleet
            is "unwanted". Therefore, one of the routes of the convoy is disrupted and that means that the complete
            convoy is disrupted. The army in London will stay in London. See also issue 4.A.1.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.russia, b.north_sea, a_london, b.belgium)
        f_english_channel = b.convoy(b.germany, b.english_channel, a_london, b.belgium)
        f_mid_atlantic_ocean = b.move(b.france, UnitType.FLEET, b.mid_atlantic_ocean, b.english_channel)
        f_brest = b.supportMove(b.france, UnitType.FLEET, b.brest_c, f_mid_atlantic_ocean, b.english_channel)

        b.assertSuccess(a_london)
        b.assertFail(f_english_channel)
        b.assertDislodge(f_english_channel)
        b.moves_adjudicate(self)

    def test_6_f_12(self):
        """ 6.F.12. TEST CASE, DISLODGED CONVOYING FLEET NOT ON ROUTE
            When the rule is used that convoys are disrupted when one of the routes is disrupted (see issue 4.A.1),
            the convoy is not necessarily disrupted when one of the fleets ordered to convoy is dislodged.
            England: F English Channel Convoys A London - Belgium
            England: A London - Belgium
            England: F Irish Sea Convoys A London - Belgium
            France: F North Atlantic Ocean Supports F Mid-Atlantic Ocean - Irish Sea
            France: F Mid-Atlantic Ocean - Irish Sea
            Even when convoys are disrupted when one of the routes is disrupted (see issue 4.A.1), the convoy from
            London to Belgium will still succeed, since the dislodged fleet in the Irish Sea is not part of any route,
            although it can be reached from the starting point London.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_english_channel = b.convoy(b.england, b.english_channel, a_london, b.belgium)
        f_irish_sea = b.convoy(b.england, b.irish_sea, a_london, b.belgium)
        f_mid_atlantic_ocean = b.move(b.france, UnitType.FLEET, b.mid_atlantic_ocean, b.irish_sea)
        f_north_atlantic_ocean = b.supportMove(b.france, UnitType.FLEET, b.north_atlantic_ocean, f_mid_atlantic_ocean, b.irish_sea)

        b.assertSuccess(a_london)
        b.assertDislodge(f_irish_sea)
        b.moves_adjudicate(self)

    def test_6_f_13(self):
        """ 6.F.13. TEST CASE, THE UNWANTED ALTERNATIVE
            This situation is not difficult to adjudicate, but it shows that even if someone wants to convoy, the
            player might not want an alternative route for the convoy.
            England: A London - Belgium
            England: F North Sea Convoys A London - Belgium
            France: F English Channel Convoys A London - Belgium
            Germany: F Holland Supports F Denmark - North Sea
            Germany: F Denmark - North Sea
            If France and German are allies, England want to keep its army in London, to defend the island. An army
            in Belgium could easily be destroyed by an alliance of France and Germany. England tries to be friends with
            Germany, however France and Germany trick England.
            The convoy of the army in London succeeds and the fleet in Denmark dislodges the fleet in the North Sea.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.belgium)
        f_english_channel = b.convoy(b.france, b.english_channel, a_london, b.belgium)
        f_denmark = b.move(b.germany, UnitType.FLEET, b.denmark_c, b.north_sea)
        f_holland = b.supportMove(b.germany, UnitType.FLEET, b.holland_c, f_denmark, b.north_sea)

        b.assertSuccess(a_london)
        b.assertDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_f_14(self):
        """ 6.F.14. TEST CASE, SIMPLE CONVOY PARADOX
            The most common paradox is when the attacked unit supports an attack on one of the convoying fleets.
            England: F London Supports F Wales - English Channel
            England: F Wales - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            This situation depends on how paradoxes are handled (see issue (4.A.2). In case of the 'All Hold' rule
            (fully applied, not just as "backup" rule), both the movement of the English fleet in Wales as the France
            convoy in Brest are part of the paradox and fail. In all other rules of paradoxical convoys (including the
            Szykman rule which I prefer), the support of London is not cut. That means that the fleet in the English
            Channel is dislodged.
        """
        b = BoardBuilder()
        f_wales = b.move(b.england, UnitType.FLEET, b.wales_c, b.english_channel)
        f_london = b.supportMove(b.england, UnitType.FLEET, b.london_c, f_wales, b.english_channel)
        a_brest = b.move(b.france, UnitType.ARMY, b.brest, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_brest, b.london)

        b.assertSuccess(f_wales, f_london)
        b.assertDislodge(f_english_channel)
        b.assertFail(f_english_channel, a_brest)
        b.moves_adjudicate(self)

    def test_6_f_15(self):
        """ 6.F.15. TEST CASE, SIMPLE CONVOY PARADOX WITH ADDITIONAL CONVOY
            Paradox rules only apply on the paradox core.
            England: F London Supports F Wales - English Channel
            England: F Wales - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            Italy: F Irish Sea Convoys A North Africa - Wales
            Italy: F Mid-Atlantic Ocean Convoys A North Africa - Wales
            Italy: A North Africa - Wales
            The Italian convoy is not part of the paradox core and should therefore succeed when the move of the
            fleet in Wales is successful. This is the case except when the 'All Hold' paradox rule is used (fully
            applied, not just as "backup" rule, see issue 4.A.2).
            I prefer the Szykman rule, so I prefer that both the fleet in Wales as the army in North Africa succeed in
            moving.
        """
        b = BoardBuilder()
        f_wales = b.move(b.england, UnitType.FLEET, b.wales_c, b.english_channel)
        f_london = b.supportMove(b.england, UnitType.FLEET, b.london_c, f_wales, b.english_channel)
        a_brest = b.move(b.france, UnitType.ARMY, b.brest, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_brest, b.london)
        a_north_africa = b.move(b.italy, UnitType.ARMY, b.north_africa, b.wales)
        f_irish_sea = b.convoy(b.italy, b.irish_sea, a_north_africa, b.wales)
        f_mid_atlantic = b.convoy(b.italy, b.mid_atlantic_ocean, a_north_africa, b.wales)

        b.assertSuccess(f_wales, f_london, a_north_africa, f_irish_sea, f_mid_atlantic)
        b.assertDislodge(f_english_channel)
        b.assertFail(f_english_channel, a_brest)
        b.assertSuccess(a_north_africa)
        b.moves_adjudicate(self)

    def test_6_f_16(self):
        """ 6.F.16. TEST CASE, PANDIN'S PARADOX
            In Pandin's paradox, the attacked unit protects the convoying fleet by a beleaguered garrison.
            England: F London Supports F Wales - English Channel
            England: F Wales - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            Germany: F North Sea Supports F Belgium - English Channel
            Germany: F Belgium - English Channel
            In all the different rules for resolving convoy disruption paradoxes (see issue 4.A.2), the support
            of London is not cut. That means that the fleet in the English Channel is not dislodged and none of the
            units succeed to move.
        """
        b = BoardBuilder()
        f_wales = b.move(b.england, UnitType.FLEET, b.wales_c, b.english_channel)
        f_london = b.supportMove(b.england, UnitType.FLEET, b.london_c, f_wales, b.english_channel)
        a_brest = b.move(b.france, UnitType.ARMY, b.brest, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_brest, b.london)
        f_belgium = b.move(b.germany, UnitType.FLEET, b.belgium_c, b.english_channel)
        f_north_sea = b.supportMove(b.germany, UnitType.FLEET, b.north_sea, f_belgium, b.english_channel)

        b.assertFail(f_wales, a_brest, f_belgium)
        b.assertSuccess(f_london)
        b.assertNotDislodge(f_english_channel)
        b.moves_adjudicate(self)

    def test_6_f_17(self):
        """ 6.F.17. TEST CASE, PANDIN'S EXTENDED PARADOX
            In Pandin's extended paradox, the attacked unit protects the convoying fleet by a beleaguered garrison and
            the attacked unit can dislodge the unit that gives the protection.
            England: F London Supports F Wales - English Channel
            England: F Wales - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            France: F Yorkshire Supports A Brest - London
            Germany: F North Sea Supports F Belgium - English Channel
            Germany: F Belgium - English Channel
            When the 1971, 1982 or 2000 rule is used (see issue 4.A.2), the support of London is not cut. That means
            that the fleet in the English Channel is not dislodged. The convoy will succeed and dislodge the fleet in
            London. You may argue that this violates the dislodge rule, but the common interpretation is that the
            paradox convoy rules take precedence over the dislodge rule.
            If the Simon Szykman alternative is used (which I prefer), the convoy fails and the fleet in London and
            the English Channel are not dislodged. When the 'All Hold' (fully applied, not just as "backup" rule) or
            the DPTG rule is used, the result is the same as the Simon Szykman alternative. The involved moves (the
            move of the German fleet in Belgium and the convoying army in Brest) fail.
        """
        b = BoardBuilder()
        f_wales = b.move(b.england, UnitType.FLEET, b.wales_c, b.english_channel)
        f_london = b.supportMove(b.england, UnitType.FLEET, b.london_c, f_wales, b.english_channel)
        a_brest = b.move(b.france, UnitType.ARMY, b.brest, b.london)
        f_yorkshire = b.supportMove(b.france, UnitType.FLEET, b.yorkshire_c, a_brest, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_brest, b.london)
        f_belgium = b.move(b.germany, UnitType.FLEET, b.belgium_c, b.english_channel)
        f_north_sea = b.supportMove(b.germany, UnitType.FLEET, b.north_sea, f_belgium, b.english_channel)

        b.assertFail(f_belgium, a_brest, f_wales, f_english_channel)
        b.assertSuccess(f_london, f_north_sea)
        b.assertNotDislodge(f_english_channel, f_london)
        b.moves_adjudicate(self)

    def test_6_f_18(self):
        """ 6.F.18. TEST CASE, BETRAYAL PARADOX
            The betrayal paradox is comparable to Pandin's paradox, but now the attacked unit direct supports the
            convoying fleet. Of course, this will only happen when the player of the attacked unit is betrayed.
            England: F North Sea Convoys A London - Belgium
            England: A London - Belgium
            England: F English Channel Supports A London - Belgium
            France: F Belgium Supports F North Sea
            Germany: F Helgoland Bight Supports F Skagerrak - North Sea
            Germany: F Skagerrak - North Sea
            If the English convoy from London to Belgium is successful, then it cuts the France support necessary to
            hold the fleet in the North Sea (see issue 4.A.2).
            The 1971 and 2000 ruling do not give an answer on this.
            According to the 1982 ruling the French support on the North Sea will not be cut. So, the fleet in the
            North Sea will not be dislodged by the Germans and the army in London will dislodge the French army in
            Belgium.
            If the Szykman rule is followed (which I prefer), the move of the army in London will fail and will not cut
            support. That means that the fleet in the North Sea will not be dislodged. The 'All Hold' rule has the same
            result as the Szykman rule, but with a different reason. The move of the army in London and the move of the
            German fleet in Skagerrak will fail. Since a failing convoy does not result in a consistent resolution,
            the DPTG gives the same result as the 'All Hold' rule.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.belgium)
        f_english_channel = b.supportMove(b.england, UnitType.FLEET, b.english_channel, a_london, b.belgium)
        f_belgium = b.supportHold(b.france, UnitType.FLEET, b.belgium_c, f_north_sea)
        f_skagerrak = b.move(b.germany, UnitType.FLEET, b.skagerrak, b.north_sea)
        f_helgoland_bight = b.supportMove(b.germany, UnitType.FLEET, b.helgoland_bight, f_skagerrak, b.north_sea)

        b.assertFail(a_london, f_skagerrak)
        b.assertSuccess(f_belgium)
        b.assertNotDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_f_19(self):
        """ 6.F.19. TEST CASE, MULTI-ROUTE CONVOY DISRUPTION PARADOX
            The situation becomes more complex when the convoy has alternative routes.
            France: A Tunis - Naples
            France: F Tyrrhenian Sea Convoys A Tunis - Naples
            France: F Ionian Sea Convoys A Tunis - Naples
            Italy: F Naples Supports F Rome - Tyrrhenian Sea
            Italy: F Rome - Tyrrhenian Sea
            Now, two issues play a role. The ruling about disruption of convoys (issue 4.A.1) and the issue how
            paradoxes are resolved (issue 4.A.2).
            If the 1971 rule is used about multi-route convoys (when one of the routes is disrupted, the convoy fails),
            this test case is just a simple paradox. For the 1971, 1982, 2000 and Szykman paradox rule, the support of
            the fleet in Naples is not cut and the fleet in Rome dislodges the fleet in the Tyrrhenian Sea. When the
            'All Hold' rule is used, both the convoy of the army in Tunis as the move of the fleet in Rome will fail.
            When the 1982 rule is used about multi-route convoy disruption, then convoys are disrupted when all routes
            are disrupted (this is the rule I prefer). With this rule, the situation becomes paradoxical. According to
            the 1971 and 1982 paradox rules, the support given by the fleet in Naples is not cut, that means that the
            fleet in the Tyrrhenian Sea is dislodged.
            According to the 2000 ruling the fleet in the Tyrrhenian Sea is not "necessary" for the convoy and the
            support of Naples is cut and the fleet in the Tyrrhenian Sea is not dislodged.
            If the Szykman rule is used (which I prefer), the 'All Hold' rule or the DPTG, then there is no paradoxical
            situation. The support of Naples is cut and the fleet in the Tyrrhenian Sea is not dislodged.
        """
        b = BoardBuilder()
        a_tunis = b.move(b.france, UnitType.ARMY, b.tunis, b.naples)
        f_tyrrhenian_sea = b.convoy(b.france, b.tyrrhenian_sea, a_tunis, b.naples)
        f_ionian_sea = b.convoy(b.france, b.ionian_sea, a_tunis, b.naples)
        f_rome = b.move(b.italy, UnitType.FLEET, b.rome_c, b.tyrrhenian_sea)
        f_naples = b.supportMove(b.italy, UnitType.FLEET, b.naples_c, f_rome, b.tyrrhenian_sea)

        b.assertSuccess(f_tyrrhenian_sea, f_ionian_sea)
        b.assertFail(f_naples, a_tunis, f_rome)
        b.assertNotDislodge(f_tyrrhenian_sea)
        b.moves_adjudicate(self)

    def test_6_f_20(self):
        """ 6.F.20. TEST CASE, UNWANTED MULTI-ROUTE CONVOY PARADOX
            The 1982 paradox rule allows some creative defense.
            France: A Tunis - Naples
            France: F Tyrrhenian Sea Convoys A Tunis - Naples
            Italy: F Naples Supports F Ionian Sea
            Italy: F Ionian Sea Convoys A Tunis - Naples
            Turkey: F Aegean Sea Supports F Eastern Mediterranean - Ionian Sea
            Turkey: F Eastern Mediterranean - Ionian Sea
            Again, two issues play a role. The ruling about disruption of multi-route convoys (issue 4.A.1) and the
            issue how paradoxes are resolved (issue 4.A.2).
            If the 1971 rule is used about multi-route convoys (when one of the routes is disrupted, the convoy fails),
            the Italian convoy order in the Ionian Sea is not part of the convoy, because it is a foreign unit
            (according to the DPTG).
            That means that the fleet in the Ionian Sea is not a 'convoying' fleet. In all rulings the support of
            Naples on the Ionian Sea is cut and the fleet in the Ionian Sea is dislodged by the Turkish fleet in the
            Eastern Mediterranean. When the 1982 rule is used about multi-route convoy disruption, then convoys are
            disrupted when all routes are disrupted (this is the rule I prefer). With this rule, the situation becomes
            paradoxical. According to the 1971 and 1982 paradox rules, the support given by the fleet in Naples is not
            cut, that means that the fleet in the Ionian Sea is not dislodged.
            According to the 2000 ruling the fleet in the Ionian Sea is not "necessary" and the support of Naples is
            cut and the fleet in the Ionian Sea is dislodged by the Turkish fleet in the Eastern Mediterranean.
            If the Szykman rule, the 'All Hold' rule or DPTG is used, then there is no paradoxical situation. The
            support of Naples is cut and the fleet in the Ionian Sea is dislodged by the Turkish fleet in the Eastern
            Mediterranean. As you can see, the 1982 rules allows the Italian player to save its fleet in the Ionian Sea
            with a trick. I do not consider this trick as normal tactical play. I prefer the Szykman rule as one of the
            rules that does not allow this trick. According to this rule the fleet in the Ionian Sea is dislodged.
        """
        b = BoardBuilder()
        a_tunis = b.move(b.france, UnitType.ARMY, b.tunis, b.naples)
        f_tyrrhenian_sea = b.convoy(b.france, b.tyrrhenian_sea, a_tunis, b.naples)
        f_ionian_sea = b.convoy(b.italy, b.ionian_sea, a_tunis, b.naples)
        f_naples = b.supportHold(b.italy, UnitType.FLEET, b.naples_c, f_ionian_sea)
        f_eastern_mediterranean = b.move(b.turkey, UnitType.FLEET, b.eastern_mediterranean, b.ionian_sea)
        f_aegean_sea = b.supportMove(b.turkey, UnitType.FLEET, b.aegean_sea, f_eastern_mediterranean, b.ionian_sea)

        b.assertFail(a_tunis, f_naples, f_ionian_sea)
        b.assertSuccess(f_eastern_mediterranean, f_aegean_sea)
        b.assertDislodge(f_ionian_sea)
        b.moves_adjudicate(self)

    def test_6_f_21(self):
        """ 6.F.21. TEST CASE, DAD'S ARMY CONVOY
            The 1982 paradox rule has as side effect that convoying armies do not cut support in some situations that
            are not paradoxical.
            Russia: A Edinburgh Supports A Norway - Clyde
            Russia: F Norwegian Sea Convoys A Norway - Clyde
            Russia: A Norway - Clyde
            France: F Irish Sea Supports F Mid-Atlantic Ocean - North Atlantic Ocean
            France: F Mid-Atlantic Ocean - North Atlantic Ocean
            England: A Liverpool - Clyde via Convoy
            England: F North Atlantic Ocean Convoys A Liverpool - Clyde
            England: F Clyde Supports F North Atlantic Ocean
            In all rulings, except the 1982 paradox ruling, the support of the fleet in Clyde on the North Atlantic
            Ocean is cut and the French fleet in the Mid-Atlantic Ocean will dislodge the fleet in the North Atlantic
            Ocean. This is the preferred way. However, in the 1982 paradox rule (see issue 4.A.2), the support of the
            fleet in Clyde is not cut. That means that the English fleet in the North Atlantic Ocean is not dislodged.
            As you can see, the 1982 rule allows England to save its fleet in the North Atlantic Ocean in a very
            strange way. Just the support of Clyde is insufficient (if there is no convoy, the support is cut). Only
            the convoy to the area occupied by own unit, can do the trick in this situation. The embarking of troops
            in the fleet deceives the enemy so much that it works as a magic cloak. The enemy is not able to dislodge
            the fleet in the North Atlantic Ocean any more. Of course, this will only work in comedies. I prefer the
            Szykman rule as one of the rules that does not allow this trick. According to this rule (and all other
            paradox rules), the fleet in the North Atlantic is just dislodged.
        """
        b = BoardBuilder()
        a_norway = b.move(b.russia, UnitType.ARMY, b.norway, b.clyde)
        a_edinburgh = b.supportMove(b.russia, UnitType.ARMY, b.edinburgh, a_norway, b.clyde)
        f_norwegian_sea = b.convoy(b.russia, b.norwegian_sea, a_norway, b.clyde)
        f_mid_atlantic_ocean = b.move(b.france, UnitType.FLEET, b.mid_atlantic_ocean, b.north_atlantic_ocean)
        f_irish_sea = b.supportMove(b.france, UnitType.FLEET, b.irish_sea, f_mid_atlantic_ocean, b.north_atlantic_ocean)
        a_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.clyde)
        f_north_atlantic_ocean = b.convoy(b.england, b.north_atlantic_ocean, a_liverpool, b.clyde)
        f_clyde = b.supportHold(b.england, UnitType.FLEET, b.clyde_c, f_north_atlantic_ocean)

        b.assertSuccess(a_norway, f_norwegian_sea, f_mid_atlantic_ocean, f_irish_sea, a_edinburgh)
        b.assertFail(f_north_atlantic_ocean, a_liverpool, f_clyde)
        b.assertDislodge(f_north_atlantic_ocean)
        b.moves_adjudicate(self)

    def test_6_f_22(self):
        """ 6.F.22. TEST CASE, SECOND ORDER PARADOX WITH TWO RESOLUTIONS
            Two convoys are involved in a second order paradox.
            England: F Edinburgh - North Sea
            England: F London Supports F Edinburgh - North Sea
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            Germany: F Belgium Supports F Picardy - English Channel
            Germany: F Picardy - English Channel
            Russia: A Norway - Belgium
            Russia: F North Sea Convoys A Norway - Belgium
            Without any paradox rule, there are two consistent resolutions. The supports of the English fleet in London
            and the German fleet in Picardy are not cut. That means that the French fleet in the English Channel and
            the Russian fleet in the North Sea are dislodged, which makes it impossible to cut the support. The other
            resolution is that the supports of the English fleet in London the German fleet in Picardy are cut. In that
            case the French fleet in the English Channel and the Russian fleet in the North Sea will survive and will
            not be dislodged. This gives the possibility to cut the support.
            The 1971 paradox rule and the 2000 rule (see issue 4.A.2) do not have an answer on this.
            According to the 1982 rule, the supports are not cut which means that the French fleet in the English
            Channel and the Russian fleet in the North Sea are dislodged.
            The Szykman (which I prefer), has the same result as the 1982 rule. The supports are not cut, the convoying
            armies fail to move, the fleet in Picardy dislodges the fleet in English Channel and the fleet in Edinburgh
            dislodges the fleet in the North Sea.
            The DPTG rule has in this case the same result as the Szykman rule, because the failing of all convoys is a
            consistent resolution. So, the armies in Brest and Norway fail to move, while the fleets in Edinburgh and
            Picardy succeed to move. When the 'All Hold' rule is used, the movement of the armies in Brest and Norway
            as the fleets in Edinburgh and Picardy will fail.
        """
        b = BoardBuilder()
        f_edinburgh = b.move(b.england, UnitType.FLEET, b.edinburgh_c, b.north_sea)
        f_london = b.supportMove(b.england, UnitType.FLEET, b.london_c, f_edinburgh, b.north_sea)
        a_brest = b.move(b.france, UnitType.ARMY, b.brest, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_brest, b.london)
        f_picardy = b.move(b.germany, UnitType.FLEET, b.picardy_c, b.english_channel)
        f_belgium = b.supportMove(b.germany, UnitType.FLEET, b.belgium_c, f_picardy, b.english_channel)
        a_norway = b.move(b.russia, UnitType.ARMY, b.norway, b.belgium)
        f_north_sea = b.convoy(b.russia, b.north_sea, a_norway, b.belgium)

        b.assertDislodge(f_english_channel, f_north_sea)
        b.assertFail(a_brest, a_norway)
        b.assertSuccess(f_edinburgh, f_picardy, f_london, f_belgium)
        b.moves_adjudicate(self)

    def test_6_f_23(self):
        """ 6.F.23. TEST CASE, SECOND ORDER PARADOX WITH TWO EXCLUSIVE CONVOYS
            In this paradox there are two consistent resolutions, but where the two convoys do not fail or succeed at
            the same time. This fact is important for the DPTG resolution.
            England: F Edinburgh - North Sea
            England: F Yorkshire Supports F Edinburgh - North Sea
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            Germany: F Belgium Supports F English Channel
            Germany: F London Supports F North Sea
            Italy: F Mid-Atlantic Ocean - English Channel
            Italy: F Irish Sea Supports F Mid-Atlantic Ocean - English Channel
            Russia: A Norway - Belgium
            Russia: F North Sea Convoys A Norway - Belgium
            Without any paradox rule, there are two consistent resolutions. In one resolution, the convoy in the
            English Channel is dislodged by the fleet in the Mid-Atlantic Ocean, while the convoy in the North Sea
            succeeds. In the other resolution, it is the other way around. The convoy in the North Sea is dislodged by
            the fleet in Edinburgh, while the convoy in the English Channel succeeds.
            The 1971 paradox rule and the 2000 rule (see issue 4.A.2) do not have an answer on this.
            According to the 1982 rule, the supports are not cut which means that the none of the units move.
            The Szykman (which I prefer), has the same result as the 1982 rule. The convoying armies fail to move and
            the supports are not cut. Because of the failure to cut the support, no fleet succeeds to move.
            When the 'All Hold' rule is used, the movement of the armies and the fleets all fail.
            Since there is no consistent resolution where all convoys fail, the DPTG rule has the same result as the
            'All Hold' rule. That means the movement of all units fail.
        """
        b = BoardBuilder()
        f_edinburgh = b.move(b.england, UnitType.FLEET, b.edinburgh_c, b.north_sea)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, f_edinburgh, b.north_sea)
        a_brest = b.move(b.france, UnitType.ARMY, b.brest, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_brest, b.london)
        f_belgium = b.supportHold(b.germany, UnitType.FLEET, b.belgium_c, f_english_channel)
        f_mid_atlantic_ocean = b.move(b.italy, UnitType.FLEET, b.mid_atlantic_ocean, b.english_channel)
        f_irish_sea = b.supportMove(b.italy, UnitType.FLEET, b.irish_sea, f_mid_atlantic_ocean, b.english_channel)
        a_norway = b.move(b.russia, UnitType.ARMY, b.norway, b.belgium)
        f_north_sea = b.convoy(b.russia, b.north_sea, a_norway, b.belgium)
        f_london = b.supportHold(b.germany, UnitType.FLEET, b.london_c, f_north_sea)

        b.assertFail(f_mid_atlantic_ocean, f_edinburgh, a_brest, a_norway)
        b.assertSuccess(f_belgium, f_london)
        b.assertNotDislodge(f_english_channel, f_north_sea)
        b.moves_adjudicate(self)

    def test_6_f_24(self):
        """ 6.F.24. TEST CASE, SECOND ORDER PARADOX WITH NO RESOLUTION
            As first order paradoxes, second order paradoxes come in two flavors, with two resolutions or no resolution.
            England: F Edinburgh - North Sea
            England: F London Supports F Edinburgh - North Sea
            England: F Irish Sea - English Channel
            England: F Mid-Atlantic Ocean Supports F Irish Sea - English Channel
            France: A Brest - London
            France: F English Channel Convoys A Brest - London
            France: F Belgium Supports F English Channel
            Russia: A Norway - Belgium
            Russia: F North Sea Convoys A Norway - Belgium
            When no paradox rule is used, there is no consistent resolution. If the French support in Belgium is cut,
            the French fleet in the English Channel will be dislodged. That means that the support of London will not
            be cut and the fleet in Edinburgh will dislodge the Russian fleet in the North Sea. In this way the support
            in Belgium is not cut! But if the support in Belgium is not cut, the Russian fleet in the North Sea will
            not be dislodged and the army in Norway can cut the support in Belgium.
            The 1971 paradox rule and the 2000 rule (see issue 4.A.2) do not have an answer on this. According to the
            1982 rule, the supports are not cut which means that the French fleet in the English Channel will survive
            and but the Russian fleet in the North Sea is dislodged.
            If the Szykman alternative is used (which I prefer), the supports are not cut and the convoying armies fail
            to move, which has the same result as the 1982 rule in this case.
            When the 'All Hold' rule is used, the movement of the armies in Brest and Norway as the fleets in Edinburgh
            and the Irish Sea will fail. Since there is no consistent resolution where all convoys fail, the DPTG has
            in this case the same result as the 'All Hold' rule.
        """
        b = BoardBuilder()
        f_edinburgh = b.move(b.england, UnitType.FLEET, b.edinburgh_c, b.north_sea)
        f_london = b.supportMove(b.england, UnitType.FLEET, b.london_c, f_edinburgh, b.north_sea)
        f_irish_sea = b.move(b.england, UnitType.FLEET, b.irish_sea, b.english_channel)
        f_mid_atlantic_ocean = b.supportMove(b.england, UnitType.FLEET, b.mid_atlantic_ocean, f_irish_sea, b.english_channel)
        a_brest = b.move(b.france, UnitType.ARMY, b.brest, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_brest, b.london)
        f_belgium = b.supportHold(b.france, UnitType.FLEET, b.belgium_c, f_english_channel)
        a_norway = b.move(b.russia, UnitType.ARMY, b.norway, b.belgium)
        f_north_sea = b.convoy(b.russia, b.north_sea, a_norway, b.belgium)

        b.assertSuccess(f_london, f_belgium, f_edinburgh, f_mid_atlantic_ocean)
        b.assertFail(a_brest, a_norway, f_irish_sea)
        b.assertNotDislodge(f_english_channel)
        b.assertDislodge(f_north_sea)
        b.moves_adjudicate(self)

    def test_6_g_1(self):
        """ 6.G.1. TEST CASE, TWO UNITS CAN SWAP PLACES BY CONVOY
            The only way to swap two units, is by convoy.
            England: A Norway - Sweden
            England: F Skagerrak Convoys A Norway - Sweden
            Russia: A Sweden - Norway
            In most interpretation of the rules, the units in Norway and Sweden will be swapped. However, if
            explicit adjacent convoying is used (see issue 4.A.3), then it is just a head to head battle.
            I prefer the 2000 rules, so the units are swapped.
        """
        b = BoardBuilder()
        a_norway = b.move(b.england, UnitType.ARMY, b.norway, b.sweden)
        f_skagerrak = b.convoy(b.england, b.skagerrak, a_norway, b.sweden)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway)

        b.assertSuccess(a_norway, f_skagerrak, a_sweden)
        b.moves_adjudicate(self)

    def test_6_g_2(self):
        """ 6.G.2. TEST CASE, KIDNAPPING AN ARMY
            Germany promised England to support to dislodge the Russian fleet in Sweden and it promised Russia to
            support to dislodge the English army in Norway. Instead, the joking German orders a convoy.
            England: A Norway - Sweden
            Russia: F Sweden - Norway
            Germany: F Skagerrak Convoys A Norway - Sweden
            See issue 4.A.3.
            When the 1982/2000 rulebook is used (which I prefer), England has no intent to swap and it is just a head
            to head battle were both units will fail to move. When explicit adjacent convoying is used (DPTG), the
            English move is not a convoy and again it just a head to head battle were both units will fail to move.
            In all other interpretations, the army in Norway will be convoyed and swap its place with the fleet in
            Sweden.
        """
        b = BoardBuilder()
        a_norway = b.move(b.england, UnitType.ARMY, b.norway, b.sweden)
        f_skagerrak = b.convoy(b.germany, b.skagerrak, a_norway, b.sweden)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway)
        
        b.assertSuccess(a_norway, a_norway)
        b.moves_adjudicate(self)

    def test_6_g_3(self):
        """ 6.G.3. TEST CASE, KIDNAPPING WITH A DISRUPTED CONVOY
            When kidnapping of armies is allowed, a move can be sabotaged by a fleet that is almost certainly dislodged.
            France: F Brest - English Channel
            France: A Picardy - Belgium
            France: A Burgundy Supports A Picardy - Belgium
            France: F Mid-Atlantic Ocean Supports F Brest - English Channel
            England: F English Channel Convoys A Picardy - Belgium
            See issue 4.A.3. If a convoy always takes precedence over a land route (choice a), the move from Picardy to
            Belgium fails. It tries to convoy and the convoy is disrupted.
            For choice b and c, there is no unit moving in opposite direction for the move of the army in Picardy.
            For this reason, the move for the army in Picardy is not by convoy and succeeds over land.
            When the 1982 or 2000 rules are used (choice d), then it is not the "intent" of the French army in Picardy
            to convoy. The move from Picardy to Belgium is just a successful move over land.
            When explicit adjacent convoying is used (DPTG, choice e), the order of the French army in Picardy is not
            a convoy order. So, it just ordered over land, and that move succeeds. This is an excellent example why
            the convoy route should not automatically have priority over the land route. It would just be annoying for
            the attacker and this situation is without fun. I prefer the 1982 rule with the 2000 clarification.
            According to these rules the move from Picardy succeeds.
        """
        b = BoardBuilder()
        f_brest = b.move(b.france, UnitType.FLEET, b.brest_c, b.english_channel)
        a_picardy = b.move(b.france, UnitType.ARMY, b.picardy, b.belgium)
        a_burgundy = b.supportMove(b.france, UnitType.ARMY, b.burgundy, a_picardy, b.belgium)
        a_mid_atlantic_ocean = b.supportMove(b.france, UnitType.FLEET, b.mid_atlantic_ocean, f_brest, b.english_channel)
        f_english_channel = b.convoy(b.england, b.english_channel, a_picardy, b.belgium)
        
        b.assertSuccess(f_brest, a_picardy, a_burgundy, a_mid_atlantic_ocean)
        b.assertFail(f_english_channel)
        b.assertDislodge(f_english_channel)
        b.moves_adjudicate(self)

    def test_6_g_4(self):
        """ 6.G.4. TEST CASE, KIDNAPPING WITH A DISRUPTED CONVOY AND OPPOSITE MOVE
            In the situation of the previous test case it was rather clear that the army didn't want to take the
            convoy. But what if there is an army moving in opposite direction?
            France: F Brest - English Channel
            France: A Picardy - Belgium
            France: A Burgundy Supports A Picardy - Belgium
            France: F Mid-Atlantic Ocean Supports F Brest - English Channel
            England: F English Channel Convoys A Picardy - Belgium
            England: A Belgium - Picardy
            See issue 4.A.3. If a convoy always takes precedence over a land route (choice a), the move from Picardy to
            Belgium fails. It tries to convoy and the convoy is disrupted.
            For choice b the convoy is also taken, because there is a unit in Belgium moving in opposite direction.
            This means that the convoy is disrupted and the move from Picardy to Belgium fails.
            For choice c the convoy is not taken. Although, the unit in Belgium is moving in opposite direction,
            the army will not take a disrupted convoy. So, the move from Picardy to Belgium succeeds.
            When the 1982 or 2000 rules are used (choice d), then it is not the "intent" of the French army in Picardy
            to convoy. The move from Picardy to Belgium is just a successful move over land.
            When explicit adjacent convoying is used (DPTG, choice e), the order of the French army in Picardy is not
            a convoy order. So, it just ordered over land, and that move succeeds.
            Again an excellent example why the convoy route should not automatically have priority over the land route.
            It would just be annoying for the attacker and this situation is without fun. I prefer the 1982 rule with
            the 2000 clarification. According to these rules the move from Picardy succeeds.
        """
        b = BoardBuilder()
        f_brest = b.move(b.france, UnitType.FLEET, b.brest_c, b.english_channel)
        a_picardy = b.move(b.france, UnitType.ARMY, b.picardy, b.belgium)
        a_burgundy = b.supportMove(b.france, UnitType.ARMY, b.burgundy, a_picardy, b.belgium)
        a_mid_atlantic_ocean = b.supportMove(b.france, UnitType.FLEET, b.mid_atlantic_ocean, f_brest, b.english_channel)
        f_english_channel = b.convoy(b.england, b.english_channel, a_picardy, b.belgium)
        a_belgium = b.move(b.england, UnitType.ARMY, b.belgium, b.picardy)

        b.assertSuccess(f_brest, a_picardy, a_burgundy, a_mid_atlantic_ocean)
        b.assertFail(f_english_channel, a_belgium)
        b.assertDislodge(f_english_channel, a_belgium)
        b.moves_adjudicate(self)

    def test_6_g_5(self):
        """ 6.G.5. TEST CASE, SWAPPING WITH INTENT
            When one of the convoying fleets is of the same nationality of the convoyed army, the "intent" is to convoy.
            Italy: A Rome - Apulia
            Italy: F Tyrrhenian Sea Convoys A Apulia - Rome
            Turkey: A Apulia - Rome
            Turkey: F Ionian Sea Convoys A Apulia - Rome
            See issue 4.A.3. When the 1982/2000 rulebook is used (which I prefer), the convoy depends on the "intent".
            Since there is an own fleet in the convoy, the intent is to convoy and the armies in Rome and Apulia swap
            places. For choices a, b and c of the issue there is also a convoy and the same swap takes place.
            When explicit adjacent convoying is used (DPTG, choice e), then the Turkish army did not receive an order
            to move by convoy. So, it is just a head to head battle and both the army in Rome and Apulia will not move.
        """
        b = BoardBuilder()
        a_rome = b.move(b.italy, UnitType.ARMY, b.rome, b.apulia)
        f_tyrrhenian_sea = b.convoy(b.italy, b.tyrrhenian_sea, a_rome, b.apulia)
        a_apulia = b.move(b.turkey, UnitType.ARMY, b.apulia, b.rome)
        f_ionian_sea = b.convoy(b.turkey, b.ionian_sea, a_apulia, b.rome)

        b.assertSuccess(a_rome, a_apulia)
        b.moves_adjudicate(self)

    def test_6_g_6(self):
        """ 6.G.6. TEST CASE, SWAPPING WITH UNINTENDED INTENT
            The intent is questionable.
            England: A Liverpool - Edinburgh
            England: F English Channel Convoys A Liverpool - Edinburgh
            Germany: A Edinburgh - Liverpool
            France: F Irish Sea Hold
            France: F North Sea Hold
            Russia: F Norwegian Sea Convoys A Liverpool - Edinburgh
            Russia: F North Atlantic Ocean Convoys A Liverpool - Edinburgh
            See issue 4.A.3.
            For choice a, b and c the English army in Liverpool will move by convoy and consequentially the two armies
            are swapped. For choice d, the 1982/2000 rulebook (which I prefer), the convoy depends on the "intent".
            England intended to convoy via the French fleets in the Irish Sea and the North Sea. However, the French
            did not order the convoy. The alternative route with the Russian fleets was unintended. The English fleet
            in the English Channel (with the convoy order) is not part of this alternative route with the Russian
            fleets. Since England still "intent" to convoy, the move from Liverpool to Edinburgh should be via convoy
            and the two armies are swapped. Although, you could argue that this is not really according to the
            clarification of the 2000 rulebook. When explicit adjacent convoying is used (DPTG, choice e), then the
            English army did not receive an order to move by convoy. So, it is just a head to head battle and both the
            army in Edinburgh and Liverpool will not move.
        """
        b = BoardBuilder()
        a_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.edinburgh)
        f_english_channel = b.convoy(b.england, b.english_channel, a_liverpool, b.edinburgh)
        f_irish_sea = b.hold(b.france, UnitType.FLEET, b.irish_sea)
        f_north_sea = b.hold(b.france, UnitType.FLEET, b.north_sea)
        a_edinburgh = b.move(b.germany, UnitType.ARMY, b.edinburgh, b.liverpool)
        f_norwegian_sea = b.convoy(b.russia, b.norwegian_sea, a_liverpool, b.edinburgh)
        f_north_atlantic_ocean = b.convoy(b.russia, b.north_atlantic_ocean, a_liverpool, b.edinburgh)
        
        b.assertSuccess(a_liverpool, a_edinburgh)
        b.moves_adjudicate(self)

    def test_6_g_7(self):
        """ 6.G.7. TEST CASE, SWAPPING WITH ILLEGAL INTENT
            Can the intent made clear with an impossible order?
            England: F Skagerrak Convoys A Sweden - Norway
            England: F Norway - Sweden
            Russia: A Sweden - Norway
            Russia: F Gulf of Bothnia Convoys A Sweden - Norway
            See issue 4.A.3 and 4.E.1.
            If for issue 4.A.3 choice a, b or c has been taken, then the army in Sweden moves by convoy and swaps
            places with the fleet in Norway.
            However, if for issue 4.A.3 the 1982/2000 has been chosen (choice d), then the "intent" is important.
            The question is whether the fleet in the Gulf of Bothnia can express the intent. If the order for this
            fleet is considered illegal (see issue 4.E.1), then this order must be ignored and there is no intent to
            swap. In that case none of the units move. If explicit convoying is used (DPTG, choice e of issue 4.A.3)
            then the army in Sweden will take the land route and none of the units move.
            I prefer the 1982/2000 rule and that any orders that can't be valid are illegal. So, the order of the fleet
            in the Gulf of Bothnia is ignored and can not show the intent. There is no convoy, so no unit will move.
        """
        b = BoardBuilder()
        f_norway = b.move(b.england, UnitType.FLEET, b.norway_c, b.sweden_c)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway)
        f_skagerrak = b.convoy(b.england, b.skagerrak, a_sweden, b.norway)
        f_gulf_of_bothnia = b.convoy(b.russia, b.gulf_of_bothnia, a_sweden, b.norway)
        b.assertSuccess(f_norway, a_sweden)
        b.moves_adjudicate(self)

    def test_6_g_8(self):
        """ 6.G.8. TEST CASE, EXPLICIT CONVOY THAT ISN'T THERE
            What to do when a unit is explicitly ordered to move via convoy and the convoy is not there?
            France: A Belgium - Holland via Convoy
            England: F North Sea - Helgoland Bight
            England: A Holland - Kiel
            The French army in Belgium intended to move convoyed with the English fleet in the North Sea. But the
            English changed their plans.
            See issue 4.A.3.
            If choice a, b or c has been taken, then the 'via Convoy' directive has no meaning and the army in Belgium
            will move to Holland. If the 1982/2000 rulebook is used (choice d, which I prefer), the "via Convoy" has
            meaning, but only when there is both a land route and a convoy route. Since there is no convoy the
            "via Convoy" directive should be ignored. And the move from Belgium to Holland succeeds.
            If explicit adjacent convoying is used (DPTG, choice e), then the unit can only go by convoy. Since there
            is no convoy, the move from Belgium to Holland fails.
        """
        b = BoardBuilder()
        a_belgium = b.move(b.france, UnitType.ARMY, b.belgium, b.holland)
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.helgoland_bight)
        a_holland = b.move(b.england, UnitType.ARMY, b.holland, b.kiel)
        b.assertSuccess(a_belgium, f_north_sea, a_holland)
        b.moves_adjudicate(self)

    def test_6_g_9(self):
        """ 6.G.9. TEST CASE, SWAPPED OR DISLODGED?
            The 1982 rulebook says that whether the move is over land or via convoy depends on the "intent" as shown
            by the totality of the orders written by the player governing the army (see issue 4.A.3). In this test
            case the English army in Norway will end in all cases in Sweden. But whether it is convoyed or not has
            effect on the Russian army. In case of convoy the Russian army ends in Norway and in case of a land route
            the Russian army is dislodged.
            England: A Norway - Sweden
            England: F Skagerrak Convoys A Norway - Sweden
            England: F Finland Supports A Norway - Sweden
            Russia: A Sweden - Norway
            See issue 4.A.3.
            For choice a, b and c the move of the army in Norway is by convoy and the armies in Norway and Sweden are
            swapped. If the 1982 rulebook is used with the clarification of the 2000 rulebook (choice d, which I
            prefer), the intent of the English player is to convoy, since it ordered the fleet in Skagerrak to convoy.
            Therefore, the armies in Norway and Sweden are swapped. When explicit adjacent convoying is used (DTPG,
            choice e), then the unit in Norway did not receive an order to move by convoy and the land route should be
            considered. The Russian army in Sweden is dislodged.
        """
        b = BoardBuilder()
        
        a_norway = b.move(b.england, UnitType.ARMY, b.norway, b.sweden)
        f_skagerrak = b.convoy(b.england, b.skagerrak, a_norway, b.sweden)
        f_finland = b.supportMove(b.england, UnitType.FLEET, b.finland_c, a_norway, b.sweden)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway)

        b.assertSuccess(a_norway, a_sweden)
        b.moves_adjudicate(self)

    def test_6_g_10(self):
        """ 6.G.10. TEST CASE, SWAPPED OR AN HEAD TO HEAD BATTLE?
            Can a dislodged unit have effect on the attackers area, when the attacker moved by convoy?
            England: A Norway - Sweden via Convoy
            England: F Denmark Supports A Norway - Sweden
            England: F Finland Supports A Norway - Sweden
            Germany: F Skagerrak Convoys A Norway - Sweden
            Russia: A Sweden - Norway
            Russia: F Barents Sea Supports A Sweden - Norway
            France: F Norwegian Sea - Norway
            France: F North Sea Supports F Norwegian Sea - Norway
            Since England ordered the army in Norway to move explicitly via convoy and the army in Sweden is moving
            in opposite direction, only the convoyed route should be considered regardless of the rulebook used. It
            is clear that the army in Norway will dislodge the Russian army in Sweden. Since the strength of three is
            in all cases the strongest force. The army in Sweden will not advance to Norway, because it can not beat
            the force in the Norwegian Sea. It will be dislodged by the army from Norway.
            The more interesting question is whether French fleet in the Norwegian Sea is bounced by the Russian army
            from Sweden. This depends on the interpretation of issue 4.A.7. If the rulebook is taken literally
            (choice a), then a dislodged unit can not bounce a unit in the area where the attacker came from. This
            would mean that the move of the fleet in the Norwegian Sea succeeds However, if choice b is taken
            (which I prefer), then a bounce is still possible, when there is no head to head battle. So, the fleet in
            the Norwegian Sea will fail to move.
        """
        b = BoardBuilder()
        a_norway = b.move(b.england, UnitType.ARMY, b.norway, b.sweden)
        f_denmark = b.supportMove(b.england, UnitType.FLEET, b.denmark_c, a_norway, b.sweden)
        f_finland = b.supportMove(b.england, UnitType.FLEET, b.finland_c, a_norway, b.sweden)
        f_skagerrak = b.convoy(b.germany, b.skagerrak, a_norway, b.sweden)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway);
        f_barents_sea = b.supportMove(b.russia, UnitType.FLEET, b.barents_sea, a_sweden, b.norway)
        f_norwegian_sea = b.move(b.france, UnitType.FLEET, b.norwegian_sea, b.norway_c)
        f_north_sea = b.supportMove(b.france, UnitType.FLEET, b.north_sea, f_norwegian_sea, b.norway_c)

        b.assertDislodge(a_sweden)
        b.assertSuccess(f_denmark, f_finland, f_skagerrak, a_norway)
        b.assertFail(f_norwegian_sea, a_sweden)
        b.moves_adjudicate(self)

    def test_6_g_11(self):
        """ 6.G.11. TEST CASE, A CONVOY TO AN ADJACENT PLACE WITH A PARADOX
            In this case the convoy route is available when the land route is chosen and the convoy route is not
            available when the convoy route is chosen.
            England: F Norway Supports F North Sea - Skagerrak
            England: F North Sea - Skagerrak
            Russia: A Sweden - Norway
            Russia: F Skagerrak Convoys A Sweden - Norway
            Russia: F Barents Sea Supports A Sweden - Norway
            See issue 4.A.2 and 4.A.3.
            If for issue 4.A.3, choice b, c or e has been taken, then the move from Sweden to Norway is not a
            convoy and the English fleet in Norway is dislodged and the fleet in Skagerrak will not be dislodged.
            If choice a or d (1982/2000 rule) has been taken for issue 4.A.3, then the move from Sweden to Norway
            must be treated as a convoy. At that moment the situation becomes paradoxical. When the 'All Hold' rule is
            used, both the army in Sweden as the fleet in the North Sea will not advance. In all other paradox rules
            the English fleet in the North Sea will dislodge the Russian fleet in Skagerrak and the army in Sweden will
            not advance.
            I prefer the 1982 rule with the 2000 rulebook clarification concerning the convoy to adjacent places and
            I prefer the Szykman rule for paradox resolving. That means that according to these preferences the fleet
            in the North Sea will dislodge the Russian fleet in Skagerrak and the army in Sweden will not advance.
        """
        b = BoardBuilder()
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.skagerrak)
        f_norway = b.supportMove(b.england, UnitType.FLEET, b.norway_c, f_north_sea, b.skagerrak)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway)
        f_skagerrak = b.convoy(b.russia, b.skagerrak, a_sweden, b.norway)
        f_barents = b.supportMove(b.russia, UnitType.FLEET, b.barents_sea, a_sweden, b.norway)
        
        b.assertDislodge(f_norway)
        b.assertSuccess(a_sweden)
        b.assertFail(f_norway)
        b.assertNotDislodge(f_skagerrak)
        b.moves_adjudicate(self)

    def test_6_g_12(self):
        """ 6.G.12. TEST CASE, SWAPPING TWO UNITS WITH TWO CONVOYS
            Of course, two armies can also swap by when they are both convoyed.
            England: A Liverpool - Edinburgh via Convoy
            England: F North Atlantic Ocean Convoys A Liverpool - Edinburgh
            England: F Norwegian Sea Convoys A Liverpool - Edinburgh
            Germany: A Edinburgh - Liverpool via Convoy
            Germany: F North Sea Convoys A Edinburgh - Liverpool
            Germany: F English Channel Convoys A Edinburgh - Liverpool
            Germany: F Irish Sea Convoys A Edinburgh - Liverpool
            The armies in Liverpool and Edinburgh are swapped.
        """
        b = BoardBuilder()
        a_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.edinburgh)
        f_north_atlantic = b.convoy(b.england, b.north_atlantic_ocean, a_liverpool, b.edinburgh)
        f_norwegian_sea = b.convoy(b.england, b.norwegian_sea, a_liverpool, b.edinburgh)
        
        a_edinburgh = b.move(b.germany, UnitType.ARMY, b.edinburgh, b.liverpool)
        f_north_sea = b.convoy(b.germany, b.north_sea, a_edinburgh, b.liverpool)
        f_english_channel = b.convoy(b.germany, b.english_channel, a_edinburgh, b.liverpool)
        f_irish_sea = b.convoy(b.germany, b.irish_sea, a_edinburgh, b.liverpool)

        # Assert the convoy movements
        b.assertSuccess(f_north_atlantic, f_norwegian_sea, a_liverpool)  # England's convoy to Edinburgh
        b.assertSuccess(f_north_sea, f_english_channel, f_irish_sea, a_edinburgh)  # Germany's convoy to Liverpool

        # Adjudicate the moves to finalize the state
        b.moves_adjudicate(self)

    def test_6_g_13(self):
        """ 6.G.13. TEST CASE, SUPPORT CUT ON ATTACK ON ITSELF VIA CONVOY
            If a unit is attacked by a supported unit, it is not possible to prevent dislodgement by trying to cut
            the support. But what, if a move is attempted via a convoy?
            Austria: F Adriatic Sea Convoys A Trieste - Venice
            Austria: A Trieste - Venice via Convoy
            Italy: A Venice Supports F Albania - Trieste
            Italy: F Albania - Trieste
            First it should be mentioned that if for issue 4.A.3 choice b or c is taken, then the move from Trieste
            to Venice is just a move over land, because the army in Venice is not moving in opposite direction. In that
            case, the support of Venice will not be cut as normal.
            In any other choice for issue 4.A.3, it should be decided whether the Austrian attack is considered to be
            coming from Trieste or from the Adriatic Sea. If it comes from Trieste, the support in Venice is not cut
            and the army in Trieste is dislodged by the fleet in Albania. If the Austrian attack is considered to be
            coming from the Adriatic Sea, then the support is cut and the army in Trieste will not be dislodged. See
            also issue 4.A.4. First of all, I prefer the 1982/2000 rules for adjacent convoying. This means that I
            prefer the move from Trieste uses the convoy. Furthermore, I think that the two Italian units are still
            stronger than the army in Trieste. Therefore, I prefer that the support in Venice is not cut and that the
            army in Trieste is dislodged by the fleet in Albania.
        """
        b = BoardBuilder()
        a_trieste = b.move(b.austria, UnitType.ARMY, b.trieste, b.venice)
        f_adriatic_sea = b.convoy(b.austria, b.adriatic_sea, a_trieste, b.venice)

        # Italy's setup (support and move)
        f_albania = b.move(b.italy, UnitType.FLEET, b.albania_c, b.trieste_c)
        a_venice = b.supportMove(b.italy, UnitType.ARMY, b.venice, f_albania, b.trieste_c)

        b.assertFail(a_trieste)
        b.assertDislodge(a_trieste)
        b.assertSuccess(f_albania)

        b.moves_adjudicate(self)

    def test_6_g_14(self):
        """ 6.G.14. TEST CASE, BOUNCE BY CONVOY TO ADJACENT PLACE
            Similar to test case 6.G.10, but now the other unit is taking the convoy.
            England: A Norway - Sweden
            England: F Denmark Supports A Norway - Sweden
            England: F Finland Supports A Norway - Sweden
            France: F Norwegian Sea - Norway
            France: F North Sea Supports F Norwegian Sea - Norway
            Germany: F Skagerrak Convoys A Sweden - Norway
            Russia: A Sweden - Norway via Convoy
            Russia: F Barents Sea Supports A Sweden - Norway
            Again the army in Sweden is bounced by the fleet in the Norwegian Sea. The army in Norway will move to
            Sweden and dislodge the Russian army.
            The final destination of the fleet in the Norwegian Sea depends on how issue 4.A.7 is resolved. If
            choice a is taken, then the fleet advances to Norway, but if choice b is taken (which I prefer) the fleet
            bounces and stays in the Norwegian Sea.
        """
        b = BoardBuilder()
        a_norway = b.move(b.england, UnitType.ARMY, b.norway, b.sweden)
        f_denmark = b.supportMove(b.england, UnitType.FLEET, b.denmark_c, a_norway, b.sweden)
        f_finland = b.supportMove(b.england, UnitType.FLEET, b.finland_c, a_norway, b.sweden)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway);
        f_skagerrak = b.convoy(b.germany, b.skagerrak, a_sweden, b.norway)
        f_barents_sea = b.supportMove(b.russia, UnitType.FLEET, b.barents_sea, a_sweden, b.norway)
        f_norwegian_sea = b.move(b.france, UnitType.FLEET, b.norwegian_sea, b.norway_c)
        f_north_sea = b.supportMove(b.france, UnitType.FLEET, b.north_sea, f_norwegian_sea, b.norway_c)

        b.assertDislodge(a_sweden)
        b.assertSuccess(f_denmark, f_finland, f_skagerrak, a_norway)
        b.assertFail(f_norwegian_sea, a_sweden)
        b.moves_adjudicate(self)

    def test_6_g_15(self):
        """ 6.G.15. TEST CASE, BOUNCE AND DISLODGE WITH DOUBLE CONVOY
            Similar to test case 6.G.10, but now both units use a convoy and without some support.
            England: F North Sea Convoys A London - Belgium
            England: A Holland Supports A London - Belgium
            England: A Yorkshire - London
            England: A London - Belgium via Convoy
            France: F English Channel Convoys A Belgium - London
            France: A Belgium - London via Convoy
            The French army in Belgium is bounced by the army from Yorkshire. The army in London move to Belgium,
            dislodging the unit there.
            The final destination of the army in the Yorkshire depends on how issue 4.A.7 is resolved. If choice a is
            taken, then the army advances to London, but if choice b is taken (which I prefer) the army bounces and
            stays in Yorkshire.
        """
        b = BoardBuilder()
        a_yorkshire = b.move(b.england, UnitType.ARMY, b.yorkshire, b.london)
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.belgium)
        a_holland = b.supportMove(b.england, UnitType.ARMY, b.holland, a_london, b.belgium)
        a_belgium = b.move(b.france, UnitType.ARMY, b.belgium, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_belgium, b.london)

        b.assertDislodge(a_belgium)
        b.assertSuccess(a_london)
        b.assertFail(a_belgium, a_yorkshire)
        b.moves_adjudicate(self)

    def test_6_g_16(self):
        """ 6.G.16. TEST CASE, THE TWO UNIT IN ONE AREA BUG, MOVING BY CONVOY
            If the adjudicator is not correctly implemented, this may lead to a resolution where two units end up in
            the same area.
            England: A Norway - Sweden
            England: A Denmark Supports A Norway - Sweden
            England: F Baltic Sea Supports A Norway - Sweden
            England: F North Sea - Norway
            Russia: A Sweden - Norway via Convoy
            Russia: F Skagerrak Convoys A Sweden - Norway
            Russia: F Norwegian Sea Supports A Sweden - Norway
            See decision details 5.B.6. If the 'PREVENT STRENGTH' is incorrectly implemented, due to the fact that it
            does not take into account that the 'PREVENT STRENGTH' is only zero when the unit is engaged in a head to
            head battle, then this goes wrong in this test case. The 'PREVENT STRENGTH' of Sweden would be zero,
            because the opposing unit in Norway successfully moves. Since, this strength would be zero, the fleet in
            the North Sea would move to Norway. However, although the 'PREVENT STRENGTH' is zero, the army in Sweden
            would also move to Norway. So, the final result would contain two units that successfully moved to Norway.
            Of course, this is incorrect. Norway will indeed successfully move to Sweden while the army in Sweden ends
            in Norway, because it is stronger then the fleet in the North Sea. This fleet will stay in the North Sea.
        """
        b = BoardBuilder()
        a_norway = b.move(b.england, UnitType.ARMY, b.norway, b.sweden)
        f_denmark = b.supportMove(b.england, UnitType.FLEET, b.denmark_c, a_norway, b.sweden)
        f_baltic_sea = b.supportMove(b.england, UnitType.FLEET, b.baltic_sea, a_norway, b.sweden)
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.norway_c)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway);
        f_skagerrak = b.convoy(b.russia, b.skagerrak, a_sweden, b.norway)
        f_norwegian_sea = b.supportMove(b.russia, UnitType.FLEET, b.norwegian_sea, a_sweden, b.norway)

        b.assertFail(f_north_sea)
        b.assertSuccess(a_norway, a_sweden)
        b.moves_adjudicate(self)

    def test_6_g_17(self):
        """ 6.G.17. TEST CASE, THE TWO UNIT IN ONE AREA BUG, MOVING OVER LAND
            Similar to the previous test case, but now the other unit moves by convoy.
            England: A Norway - Sweden via Convoy
            England: A Denmark Supports A Norway - Sweden
            England: F Baltic Sea Supports A Norway - Sweden
            England: F Skagerrak Convoys A Norway - Sweden
            England: F North Sea - Norway
            Russia: A Sweden - Norway
            Russia: F Norwegian Sea Supports A Sweden - Norway
            Sweden and Norway are swapped, while the fleet in the North Sea will bounce.
        """
        b = BoardBuilder()
        a_norway = b.move(b.england, UnitType.ARMY, b.norway, b.sweden)
        f_denmark = b.supportMove(b.england, UnitType.FLEET, b.denmark_c, a_norway, b.sweden)
        f_baltic_sea = b.supportMove(b.england, UnitType.FLEET, b.baltic_sea, a_norway, b.sweden)
        f_skagerrak = b.convoy(b.russia, b.skagerrak, a_norway, b.sweden)
        f_north_sea = b.move(b.england, UnitType.FLEET, b.north_sea, b.norway_c)
        a_sweden = b.move(b.russia, UnitType.ARMY, b.sweden, b.norway);
        f_norwegian_sea = b.supportMove(b.russia, UnitType.FLEET, b.norwegian_sea, a_sweden, b.norway)

        b.assertFail(f_north_sea)
        b.assertSuccess(a_norway, a_sweden)
        b.moves_adjudicate(self)

    def test_6_g_18(self):
        """ 6.G.18. TEST CASE, THE TWO UNIT IN ONE AREA BUG, WITH DOUBLE CONVOY
            Similar to the previous test case, but now both units move by convoy.
            England: F North Sea Convoys A London - Belgium
            England: A Holland Supports A London - Belgium
            England: A Yorkshire - London
            England: A London - Belgium
            England: A Ruhr Supports A London - Belgium
            France: F English Channel Convoys A Belgium - London
            France: A Belgium - London
            France: A Wales Supports A Belgium - London
            Belgium and London are swapped, while the army in Yorkshire fails to move to London.
        """
        b = BoardBuilder()
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.belgium)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.belgium)
        a_holland = b.supportMove(b.england, UnitType.ARMY, b.holland, a_london, b.belgium)
        a_ruhr = b.supportMove(b.england, UnitType.ARMY, b.ruhr, a_london, b.belgium)
        a_yorkshire = b.move(b.england, UnitType.ARMY, b.yorkshire, b.london)
        a_belgium = b.move(b.france, UnitType.ARMY, b.belgium, b.london)
        f_english_channel = b.convoy(b.france, b.english_channel, a_belgium, b.london)
        a_wales = b.supportMove(b.france, UnitType.ARMY, b.wales, a_belgium, b.london)

        b.assertSuccess(a_belgium, a_london)
        b.assertFail(a_yorkshire)
        b.moves_adjudicate(self)

    def test_6_h_1(self):
        """ 6.H.1. TEST CASE, NO SUPPORTS DURING RETREAT
            Supports are not allowed in the retreat phase.
            Austria: F Trieste Hold
            Austria: A Serbia Hold
            Turkey: F Greece Hold
            Italy: A Venice Supports A Tyrolia - Trieste
            Italy: A Tyrolia - Trieste
            Italy: F Ionian Sea - Greece
            Italy: F Aegean Sea Supports F Ionian Sea - Greece
            The fleet in Trieste and the fleet in Greece are dislodged. If the retreat orders are as follows:
            Austria: F Trieste - Albania
            Austria: A Serbia Supports F Trieste - Albania
            Turkey: F Greece - Albania
            The Austrian support order is illegal. Both dislodged fleets are disbanded.
        """
        b = BoardBuilder()
        f_trieste = b.hold(b.austria, UnitType.FLEET, b.trieste_c)
        a_serbia = b.hold(b.austria, UnitType.ARMY, b.serbia)
        f_greece = b.hold(b.turkey, UnitType.FLEET, b.greece_c)
        a_tyrolia = b.move(b.italy, UnitType.ARMY, b.tyrolia, b.trieste)
        a_venice = b.supportMove(b.italy, UnitType.ARMY, b.venice, a_tyrolia, b.trieste)
        f_ionian_sea = b.move(b.italy, UnitType.FLEET, b.ionian_sea, b.greece_c)
        f_aegean_sea = b.supportMove(b.italy, UnitType.FLEET, b.aegean_sea, f_ionian_sea, b.greece_c)

        b.assertDislodge(f_trieste, f_greece)
        b.moves_adjudicate(self)

        b.retreat(f_trieste, b.albania_c)
        a_serbia.order = Support(f_trieste, b.albania_c)
        b.retreat(f_greece, b.albania_c)
        b.assertForcedDisband(f_trieste, f_greece)
        b.retreats_adjudicate(self)

    def test_6_h_2(self):
        """ 6.H.2. TEST CASE, NO SUPPORTS FROM RETREATING UNIT
            Even a retreating unit can not give support.
            England: A Liverpool - Edinburgh
            England: F Yorkshire Supports A Liverpool - Edinburgh
            England: F Norway Hold
            Germany: A Kiel Supports A Ruhr - Holland
            Germany: A Ruhr - Holland
            Russia: F Edinburgh Hold
            Russia: A Sweden Supports A Finland - Norway
            Russia: A Finland - Norway
            Russia: F Holland Hold
            The English fleet in Norway and the Russian fleets in Edinburgh and Holland are dislodged. If the
            following retreat orders are given:
            England: F Norway - North Sea
            Russia: F Edinburgh - North Sea
            Russia: F Holland Supports F Edinburgh - North Sea
            Although the fleet in Holland may receive an order, it may not support (it is disbanded).
            The English fleet in Norway and the Russian fleet in Edinburgh bounce and are disbanded.
        """
        b = BoardBuilder()
        
        a_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.edinburgh)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, a_liverpool, b.edinburgh)
        f_norway = b.hold(b.england, UnitType.FLEET, b.norway_c)
        a_ruhr = b.move(b.germany, UnitType.ARMY, b.ruhr, b.holland)
        a_kiel = b.supportMove(b.germany, UnitType.ARMY, b.kiel, a_ruhr, b.holland)
        f_edinburgh = b.hold(b.russia, UnitType.FLEET, b.edinburgh_c)
        a_finland = b.move(b.russia, UnitType.ARMY, b.finland, b.norway)
        a_sweden = b.supportMove(b.russia, UnitType.ARMY, b.sweden, a_finland, b.norway)
        f_holland = b.hold(b.russia, UnitType.FLEET, b.holland_c)

        b.assertDislodge(f_norway, f_edinburgh, f_holland)
        b.moves_adjudicate(self)
        
        b.retreat(f_norway, b.north_sea)
        f_holland.order = Support(f_edinburgh, b.north_sea)
        b.retreat(f_edinburgh, b.north_sea)

        b.assertForcedDisband(f_norway, f_edinburgh, f_holland)
        b.retreats_adjudicate(self)

    def test_6_h_3(self):
        """ 6.H.3. TEST CASE, NO CONVOY DURING RETREAT
            Convoys during retreat are not allowed.
            England: F North Sea Hold
            England: A Holland Hold
            Germany: F Kiel Supports A Ruhr - Holland
            Germany: A Ruhr - Holland
            The English army in Holland is dislodged. If England orders the following in retreat:
            England: A Holland - Yorkshire
            England: F North Sea Convoys A Holland - Yorkshire
            The convoy order is illegal. The army in Holland is disbanded.
        """
        b = BoardBuilder()
        f_north_sea = b.hold(b.england, UnitType.FLEET, b.north_sea)
        a_holland = b.hold(b.england, UnitType.ARMY, b.holland)
        a_ruhr = b.move(b.germany, UnitType.ARMY, b.ruhr, b.holland)
        f_kiel = b.supportMove(b.germany, UnitType.FLEET, b.kiel_c, a_ruhr, b.holland)

        b.assertDislodge(a_holland)
        b.moves_adjudicate(self)

        b.retreat(a_holland, b.yorkshire)
        f_north_sea.order = ConvoyTransport(a_holland, b.yorkshire)
        
        b.assertForcedDisband(a_holland)
        b.retreats_adjudicate(self)

    def test_6_h_4(self):
        """ 6.H.4. TEST CASE, NO OTHER MOVES DURING RETREAT
            Of course you may not do any other move during a retreat. But look if the adjudicator checks for it.
            England: F North Sea Hold
            England: A Holland Hold
            Germany: F Kiel Supports A Ruhr - Holland
            Germany: A Ruhr - Holland
            The English army in Holland is dislodged. If England orders the following in retreat:
            England: A Holland - Belgium
            England: F North Sea - Norwegian Sea
            The fleet in the North Sea is not dislodge, so the move is illegal.
        """
        b = BoardBuilder()
        f_north_sea = b.hold(b.england, UnitType.FLEET, b.north_sea)
        a_holland = b.hold(b.england, UnitType.ARMY, b.holland)
        a_ruhr = b.move(b.germany, UnitType.ARMY, b.ruhr, b.holland)
        f_kiel = b.supportMove(b.germany, UnitType.FLEET, b.kiel_c, a_ruhr, b.holland)

        b.assertDislodge(a_holland)
        b.moves_adjudicate(self)

        b.retreat(a_holland, b.belgium)
        f_north_sea.order = Move(b.norwegian_sea)

        b.assertNotForcedDisband(a_holland)
        b.retreats_adjudicate(self)
        self.assertTrue(f_north_sea.province == b.north_sea, "North Sea fleet should not have moved.")

    def test_6_h_5(self):
        """ 6.H.5. TEST CASE, A UNIT MAY NOT RETREAT TO THE AREA FROM WHICH IT IS ATTACKED
            Well, that would be of course stupid. Still, the adjudicator must be tested on this.
            Russia: F Constantinople Supports F Black Sea - Ankara
            Russia: F Black Sea - Ankara
            Turkey: F Ankara Hold
            Fleet in Ankara is dislodged and may not retreat to Black Sea.
        """
        b = BoardBuilder()
        f_black_sea = b.move(b.russia, UnitType.FLEET, b.black_sea, b.ankara_c)
        f_constantinople = b.supportMove(b.russia, UnitType.FLEET, b.constantinople_c, f_black_sea, b.ankara_c)
        f_ankara = b.hold(b.turkey, UnitType.FLEET, b.ankara_c)

        b.assertDislodge(f_ankara)
        b.moves_adjudicate(self)
        self.assertTrue(b.black_sea not in f_ankara.retreat_options, "Black Sea should not be in treat options")

        b.retreat(f_ankara, b.black_sea)
        b.assertForcedDisband(f_ankara)
        b.retreats_adjudicate(self)

    def test_6_h_6(self):
        """ 6.H.6. TEST CASE, UNIT MAY NOT RETREAT TO A CONTESTED AREA
            Stand off prevents retreat to the area.
            Austria: A Budapest Supports A Trieste - Vienna
            Austria: A Trieste - Vienna
            Germany: A Munich - Bohemia
            Germany: A Silesia - Bohemia
            Italy: A Vienna Hold
            The Italian army in Vienna is dislodged. It may not retreat to Bohemia.
        """
        b = BoardBuilder()
        
        a_trieste = b.move(b.austria, UnitType.ARMY, b.trieste, b.vienna)
        a_budapest = b.supportMove(b.austria, UnitType.ARMY, b.budapest, a_trieste, b.vienna)
        a_munich = b.move(b.germany, UnitType.ARMY, b.munich, b.bohemia)
        a_silesia = b.move(b.germany, UnitType.ARMY, b.silesia, b.bohemia)
        a_vienna = b.hold(b.italy, UnitType.ARMY, b.vienna)
        
        # Check outcomes for dislodging and success/failure assertions
        b.assertFail(a_munich, a_silesia)
        b.assertDislodge(a_vienna)
        b.moves_adjudicate(self)
        self.assertFalse(b.bohemia in a_vienna.retreat_options, "Bohemia should not be a retreat option")

        b.retreat(a_vienna, b.bohemia)
        b.assertForcedDisband(a_vienna)
        b.retreats_adjudicate(self)

    def test_6_h_7(self):
        """ 6.H.7. TEST CASE, MULTIPLE RETREAT TO SAME AREA WILL DISBAND UNITS
            There can only be one unit in an area.
            Austria: A Budapest Supports A Trieste - Vienna
            Austria: A Trieste - Vienna
            Germany: A Munich Supports A Silesia - Bohemia
            Germany: A Silesia - Bohemia
            Italy: A Vienna Hold
            Italy: A Bohemia Hold
            If Italy orders the following for retreat:
            Italy: A Bohemia - Tyrolia
            Italy: A Vienna - Tyrolia
            Both armies will be disbanded.
        """

        b = BoardBuilder()

        # Austria's units and their moves
        a_trieste = b.move(b.austria, UnitType.ARMY, b.trieste, b.vienna)
        a_budapest = b.supportMove(b.austria, UnitType.ARMY, b.budapest, a_trieste, b.vienna)
        a_silesia = b.move(b.germany, UnitType.ARMY, b.silesia, b.bohemia)
        a_munich = b.supportMove(b.germany, UnitType.ARMY, b.munich, a_silesia, b.bohemia)
        a_vienna = b.hold(b.italy, UnitType.ARMY, b.vienna)
        a_bohemia = b.hold(b.italy, UnitType.ARMY, b.bohemia)

        b.assertDislodge(a_bohemia, a_vienna)
        b.moves_adjudicate(self)

        b.retreat(a_bohemia, b.tyrolia)
        b.retreat(a_vienna, b.tyrolia)
        b.assertForcedDisband(a_bohemia, a_vienna)
        b.retreats_adjudicate(self)

    def test_6_h_8(self):
        """ 6.H.8. TEST CASE, TRIPLE RETREAT TO SAME AREA WILL DISBAND UNITS
            When three units retreat to the same area, then all three units are disbanded.
            England: A Liverpool - Edinburgh
            England: F Yorkshire Supports A Liverpool - Edinburgh
            England: F Norway Hold
            Germany: A Kiel Supports A Ruhr - Holland
            Germany: A Ruhr - Holland
            Russia: F Edinburgh Hold
            Russia: A Sweden Supports A Finland - Norway
            Russia: A Finland - Norway
            Russia: F Holland Hold
            The fleets in Norway, Edinburgh and Holland are dislodged. If the following retreat orders are given:
            England: F Norway - North Sea
            Russia: F Edinburgh - North Sea
            Russia: F Holland - North Sea
            All three units are disbanded.
        """
        b = BoardBuilder()

        a_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.edinburgh)
        f_yorkshire = b.supportMove(b.england, UnitType.FLEET, b.yorkshire_c, a_liverpool, b.edinburgh)
        f_norway = b.hold(b.england, UnitType.FLEET, b.norway_c)
        a_ruhr = b.move(b.germany, UnitType.ARMY, b.ruhr, b.holland)
        a_kiel = b.supportMove(b.germany, UnitType.ARMY, b.kiel, a_ruhr, b.holland)
        f_edinburgh = b.hold(b.russia, UnitType.FLEET, b.edinburgh_c)
        a_finland = b.move(b.russia, UnitType.ARMY, b.finland, b.norway)
        a_sweden = b.supportMove(b.russia, UnitType.ARMY, b.sweden, a_finland, b.norway)
        f_holland = b.hold(b.russia, UnitType.FLEET, b.holland_c)
        
        b.assertForcedDisband(f_norway, f_edinburgh, f_holland)
        b.moves_adjudicate(self)

        b.retreat(f_norway, b.north_sea)
        b.retreat(f_edinburgh, b.north_sea)
        b.retreat(f_holland, b.north_sea)

        b.assertForcedDisband(f_norway, f_edinburgh, f_holland)
        b.retreats_adjudicate(self)

    def test_6_h_9(self):
        """ 6.H.9. TEST CASE, DISLODGED UNIT WILL NOT MAKE ATTACKERS AREA CONTESTED
            An army can follow.
            England: F Helgoland Bight - Kiel
            England: F Denmark Supports F Helgoland Bight - Kiel
            Germany: A Berlin - Prussia
            Germany: F Kiel Hold
            Germany: A Silesia Supports A Berlin - Prussia
            Russia: A Prussia - Berlin
            The fleet in Kiel can retreat to Berlin.
        """
        b = BoardBuilder()

        f_helgoland_bight = b.move(b.england, UnitType.FLEET, b.helgoland_bight, b.kiel_c)
        f_denmark = b.supportMove(b.england, UnitType.FLEET, b.denmark_c, f_helgoland_bight, b.kiel_c)
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.prussia)
        f_kiel = b.hold(b.germany, UnitType.FLEET, b.kiel_c)
        a_silesia = b.supportMove(b.germany, UnitType.ARMY, b.silesia, a_berlin, b.prussia)
        a_prussia = b.move(b.russia, UnitType.ARMY, b.prussia, b.berlin)

        b.assertDislodge(f_kiel, a_prussia)
        b.moves_adjudicate(self)
        self.assertTrue(b.berlin in f_kiel.retreat_options, "Berlin should be a retreat option")

        b.retreat(f_kiel, b.berlin)
        b.assertNotForcedDisband(f_kiel)
        b.assertForcedDisband(a_prussia)
        b.retreats_adjudicate(self)

    def test_6_h_10(self):
        """ 6.H.10. TEST CASE, NOT RETREATING TO ATTACKER DOES NOT MEAN CONTESTED
            An army can not retreat to the place of the attacker. The easiest way to program that, is to mark that
            place as "contested". However, this is not correct. Another army may retreat to that place.
            England: A Kiel Hold
            Germany: A Berlin - Kiel
            Germany: A Munich Supports A Berlin - Kiel
            Germany: A Prussia Hold
            Russia: A Warsaw - Prussia
            Russia: A Silesia Supports A Warsaw - Prussia
            The armies in Kiel and Prussia are dislodged. The English army in Kiel can not retreat to Berlin, but
            the army in Prussia can retreat to Berlin. Suppose the following retreat orders are given:
            England: A Kiel - Berlin
            Germany: A Prussia - Berlin
            The English retreat to Berlin is illegal and fails (the unit is disbanded). The German retreat to Berlin is
            successful and does not bounce on the English unit.
        """
        b = BoardBuilder()

        a_kiel = b.hold(b.england, UnitType.ARMY, b.kiel)
        a_berlin = b.move(b.germany, UnitType.ARMY, b.berlin, b.kiel)
        a_munich = b.supportMove(b.germany, UnitType.ARMY, b.munich, a_berlin, b.kiel)
        a_prussia = b.hold(b.germany, UnitType.ARMY, b.prussia)
        a_warsaw = b.move(b.russia, UnitType.ARMY, b.warsaw, b.prussia)
        a_silesia = b.supportMove(b.russia, UnitType.ARMY, b.silesia, a_warsaw, b.prussia)
        
        b.moves_adjudicate(self)
        self.assertFalse(b.berlin in a_kiel.retreat_options, "Berlin should not be a retreat option for Kiel")
        self.assertTrue(b.berlin in a_prussia.retreat_options, "Berlin should be a retreat option for Kiel")

        b.retreat(a_kiel, b.berlin)
        b.retreat(a_prussia, b.berlin)

        b.assertForcedDisband(a_kiel)
        b.assertNotForcedDisband(a_prussia)
        b.retreats_adjudicate(self)

    def test_6_h_11(self):
        """ 6.H.11. TEST CASE, RETREAT WHEN DISLODGED BY ADJACENT CONVOY
            If a unit is dislodged by an army via convoy, the question arises whether the dislodged army can retreat
            to the original place of the convoyed army. This is only relevant in case the convoy was to an adjacent
            place.
            France: A Gascony - Marseilles via Convoy
            France: A Burgundy Supports A Gascony - Marseilles
            France: F Mid-Atlantic Ocean Convoys A Gascony - Marseilles
            France: F Western Mediterranean Convoys A Gascony - Marseilles
            France: F Gulf of Lyon Convoys A Gascony - Marseilles
            Italy: A Marseilles Hold
            If for issue 4.A.3 choice b or c has been taken, then the army in Gascony will not move with the use of
            the convoy, because the army in Marseilles does not move in opposite direction. This immediately means that
            the army in Marseilles may not move to Gascony when it dislodged by the army there.
            For all other choices of issue 4.A.3, the army in Gascony takes a convoy and does not pass the border of
            Gascony with Marseilles (it went a complete different direction). Now, the result depends on which rule
            is used for retreating (see issue 4.A.5).
            I prefer the 1982/2000 rule for convoying to adjacent places. This means that the move of Gascony happened
            by convoy. Furthermore, I prefer that the army in Marseilles may retreat to Gascony.
        """

        b = BoardBuilder()

        a_gascony = b.move(b.france, UnitType.ARMY, b.gascony, b.marseilles)
        a_burgundy = b.supportMove(b.france, UnitType.ARMY, b.burgundy, a_gascony, b.marseilles)
        f_mid_atlantic_ocean = b.convoy(b.france, b.mid_atlantic_ocean, a_gascony, b.marseilles)
        f_western_mediterranean = b.convoy(b.france, b.western_mediterranean, a_gascony, b.marseilles)
        f_gulf_of_lyon = b.convoy(b.france, b.gulf_of_lyon, a_gascony, b.marseilles)
        a_marseilles = b.hold(b.italy, UnitType.ARMY, b.marseilles)

        b.assertSuccess(a_gascony, a_burgundy, f_mid_atlantic_ocean, f_western_mediterranean, f_gulf_of_lyon)
        b.assertDislodge(a_marseilles)
        b.moves_adjudicate(self)
        self.assertFalse(b.gascony in a_marseilles.retreat_options, "Gascony should not be a retreat option for Kiel")

        b.retreat(a_marseilles, b.gascony)
        b.assertDisbanded(a_marseilles)
        b.retreats_adjudicate(self)

    def test_6_h_12(self):
        """ 6.H.12. TEST CASE, RETREAT WHEN DISLODGED BY ADJACENT CONVOY WHILE TRYING TO DO THE SAME
            The previous test case can be made more extra ordinary, when both armies tried to move by convoy.
            England: A Liverpool - Edinburgh via Convoy
            England: F Irish Sea Convoys A Liverpool - Edinburgh
            England: F English Channel Convoys A Liverpool - Edinburgh
            England: F North Sea Convoys A Liverpool - Edinburgh
            France: F Brest - English Channel
            France: F Mid-Atlantic Ocean Supports F Brest - English Channel
            Russia: A Edinburgh - Liverpool via Convoy
            Russia: F Norwegian Sea Convoys A Edinburgh - Liverpool
            Russia: F North Atlantic Ocean Convoys A Edinburgh - Liverpool
            Russia: A Clyde Supports A Edinburgh - Liverpool
            If for issue 4.A.3 choice c has been taken, then the army in Liverpool will not try to move by convoy,
            because the convoy is disrupted. This has as consequence that army will just advance to Edinburgh by using
            the land route. For all other choices of issue 4.A.3, both the army in Liverpool as in Edinburgh will try
            to move by convoy. The army in Edinburgh will succeed. The army in Liverpool will fail, because of the
            disrupted convoy. It is dislodged by the army of Edinburgh. Now, the question is whether the army in
            Liverpool may retreat to Edinburgh. The result depends on which rule is used for retreating (see issue
            4.A.5). I prefer the 1982/2000 rule for convoying to adjacent places. This means that the army in Liverpool
            tries the disrupted convoy. Furthermore, I prefer that the army in Liverpool may retreat to Edinburgh.
        """

        b = BoardBuilder()
        a_liverpool = b.move(b.england, UnitType.ARMY, b.liverpool, b.edinburgh)
        f_irish_sea = b.convoy(b.england, b.irish_sea, a_liverpool, b.edinburgh)
        f_english_channel = b.convoy(b.england, b.english_channel, a_liverpool, b.edinburgh)
        f_north_sea = b.convoy(b.england, b.north_sea, a_liverpool, b.edinburgh)
        f_brest = b.move(b.france, UnitType.FLEET, b.brest_c, b.english_channel)
        f_mid_atlantic_ocean = b.supportMove(b.france, UnitType.FLEET, b.mid_atlantic_ocean, f_brest, b.english_channel)
        a_edinburgh = b.move(b.russia, UnitType.ARMY, b.edinburgh, b.liverpool)
        f_norwegian_sea = b.convoy(b.russia, b.norwegian_sea, a_edinburgh, b.liverpool)
        f_north_atlantic_ocean = b.convoy(b.russia, b.north_atlantic_ocean, a_edinburgh, b.liverpool)
        a_clyde = b.supportMove(b.russia, UnitType.ARMY, b.clyde, a_edinburgh, b.liverpool)

        b.assertSuccess(a_liverpool)
        b.assertSuccess(f_brest, a_edinburgh)
        b.assertFail(f_english_channel)
        b.assertNotDislodge(a_liverpool)
        b.moves_adjudicate(self)

        # b.retreat(a_liverpool, b.edinburgh)
        
        # b.assertForcedDisband(f_english_channel)
        # b.assertNotForcedDisband(a_liverpool)
        # b.retreats_adjudicate(self)

    def test_6_h_13(self):
        """ 6.H.13. TEST CASE, NO RETREAT WITH CONVOY IN MAIN PHASE
            The places where a unit may retreat to, must be calculated during the main phase. Care should be taken
            that a convoy ordered in the main phase can not be used in the retreat phase.
            England: A Picardy Hold
            England: F English Channel Convoys A Picardy - London
            France: A Paris - Picardy
            France: A Brest Supports A Paris - Picardy
            The dislodged army in Picardy can not retreat to London.
        """
        b = BoardBuilder()

        a_picardy = b.hold(b.england, UnitType.ARMY, b.picardy)
        f_english_channel = b.convoy(b.england, b.english_channel, a_picardy, b.london)
        
        a_paris = b.move(b.france, UnitType.ARMY, b.paris, b.picardy)
        a_brest = b.supportMove(b.france, UnitType.ARMY, b.brest, a_paris, b.picardy)

        b.assertDislodge(a_picardy)
        b.moves_adjudicate(self)
        self.assertFalse(b.london in a_picardy.retreat_options, "London should not be a retreat option for Kiel")

        b.retreat(a_picardy, b.london)
        b.assertForcedDisband(a_picardy)
        b.retreats_adjudicate(self)

    def test_6_h_14(self):
        """ 6.H.14. TEST CASE, NO RETREAT WITH SUPPORT IN MAIN PHASE
            Comparable to the previous test case, a support given in the main phase can not be used in the retreat
            phase.
            England: A Picardy Hold
            England: F English Channel Supports A Picardy - Belgium
            France: A Paris - Picardy
            France: A Brest Supports A Paris - Picardy
            France: A Burgundy Hold
            Germany: A Munich Supports A Marseilles - Burgundy
            Germany: A Marseilles - Burgundy
            After the main phase the following retreat orders are given:
            England: A Picardy - Belgium
            France: A Burgundy - Belgium
            Both the army in Picardy and Burgundy are disbanded.
        """
        b = BoardBuilder()

        # England's army holds in Picardy
        a_picardy = b.hold(b.england, UnitType.ARMY, b.picardy)
        f_english_channel = b.supportMove(b.england, UnitType.FLEET, b.english_channel, a_picardy, b.belgium)
        
        a_paris = b.move(b.france, UnitType.ARMY, b.paris, b.picardy)
        a_brest = b.supportMove(b.france, UnitType.ARMY, b.brest, a_paris, b.picardy)

        a_burgundy = b.hold(b.france, UnitType.ARMY, b.burgundy)
        a_marseilles = b.move(b.germany, UnitType.ARMY, b.marseilles, b.burgundy)
        a_munich = b.supportMove(b.germany, UnitType.ARMY, b.munich, a_marseilles, b.burgundy)
        
        b.moves_adjudicate(self)

        b.retreat(a_picardy, b.belgium)
        b.retreat(a_burgundy, b.belgium)
        b.assertForcedDisband(a_picardy, a_burgundy)
        b.retreats_adjudicate(self)

    def test_6_h_15(self):
        """ 6.H.15. TEST CASE, NO COASTAL CRAWL IN RETREAT
            You can not go to the other coast from where the attacker came from.
            England: F Portugal Hold
            France: F Spain(sc) - Portugal
            France: F Mid-Atlantic Ocean Supports F Spain(sc) - Portugal
            The English fleet in Portugal is destroyed and can not retreat to Spain(nc).
        """
        b = BoardBuilder()

        f_portugal = b.hold(b.england, UnitType.FLEET, b.portugal_c)
        f_spain_sc = b.move(b.france, UnitType.FLEET, b.spain_sc, b.portugal_c)
        f_mid_atlantic_ocean = b.supportMove(b.france, UnitType.FLEET, b.mid_atlantic_ocean, f_spain_sc, b.portugal_c)

        b.moves_adjudicate(self)
        self.assertTrue(len(f_portugal.retreat_options) == 0, "Portugal should have no retreat options")

        b.retreat(f_portugal, b.spain_nc)
        b.assertForcedDisband(f_portugal)
        b.retreats_adjudicate(self)

    def test_6_h_16(self):
        """ 6.H.16. TEST CASE, CONTESTED FOR BOTH COASTS
            If a coast is contested, the other is not available for retreat.
            France: F Mid-Atlantic Ocean - Spain(nc)
            France: F Gascony - Spain(nc)
            France: F Western Mediterranean Hold
            Italy: F Tunis Supports F Tyrrhenian Sea - Western Mediterranean
            Italy: F Tyrrhenian Sea - Western Mediterranean
            The French fleet in the Western Mediterranean can not retreat to Spain(sc).
        """
        b = BoardBuilder()

        f_mid_atlantic_ocean = b.move(b.france, UnitType.FLEET, b.mid_atlantic_ocean, b.spain_nc)
        f_gascony = b.move(b.france, UnitType.FLEET, b.gascony_c, b.spain_nc)
        f_western_mediterranean = b.hold(b.france, UnitType.FLEET, b.western_mediterranean)
        f_tyrrhenian_sea = b.move(b.italy, UnitType.FLEET, b.tyrrhenian_sea, b.western_mediterranean)
        f_tunis = b.supportMove(b.italy, UnitType.FLEET, b.tunis_c, f_tyrrhenian_sea, b.western_mediterranean)
        
        b.assertForcedDisband(f_western_mediterranean)
        b.moves_adjudicate(self)
        self.assertFalse(b.spain in f_western_mediterranean.retreat_options, "Spain should not be a retreat option")
        b.retreat(f_western_mediterranean, b.spain_sc)

        b.assertForcedDisband(f_western_mediterranean)
        b.retreats_adjudicate(self)

    # DEVIATES since currently build orders are unordered
    def test_6_i_1(self):
        """ 6.I.1. TEST CASE, TOO MANY BUILD ORDERS
            Check how program reacts when someone orders too many builds.
            Germany may build one:
            Germany: Build A Warsaw
            Germany: Build A Kiel
            Germany: Build A Munich
            Program should not build all three, but handle it in an other way. See issue 4.D.4.
            I prefer that the build orders are just handled one by one until all allowed units are build. According
            to this preference, the build in Warsaw fails, the build in Kiel succeeds and the build in Munich fails.
        """
        b = BoardBuilder()
        b.inject_centers(b.germany, 1)
        b.core(b.germany, b.warsaw, b.kiel, b.munich)
        b.build(b.germany, (UnitType.ARMY, b.warsaw), (UnitType.ARMY, b.kiel), (UnitType.ARMY, b.munich))
        b.assertBuildCount(1)
        b.builds_adjudicate(self)
        
    def test_6_i_2(self):
        """ 6.I.2. TEST CASE, FLEETS CAN NOT BE BUILD IN LAND AREAS
            Physical this is possible, but it is still not allowed.
            Russia has one build and Moscow is empty.
            Russia: Build F Moscow
            See issue 4.C.4. Some game masters will change the order and build an army in Moscow.
            I prefer that the build fails.
        """
        b = BoardBuilder()
        b.inject_centers(b.russia, 1)
        b.core(b.russia, b.moscow)
        b.build(b.russia, (UnitType.FLEET, b.moscow))
        b.assertBuildCount(0)
        b.builds_adjudicate(self)

    def test_6_i_3(self):
        """ 6.I.3. TEST CASE, SUPPLY CENTER MUST BE EMPTY FOR BUILDING
            You can't have two units in a sector. So, you can't build when there is a unit in the supply center.
            Germany may build a unit but has an army in Berlin. Germany orders the following:
            Germany: Build A Berlin
            Build fails.
        """
        b = BoardBuilder()
        b.inject_centers(b.germany, 2)
        b.army(b.berlin, b.germany)
        b.core(b.germany, b.berlin)
        b.build(b.germany, (UnitType.ARMY, b.berlin))
        b.assertBuildCount(0)
        b.builds_adjudicate(self)

    def test_6_i_4(self):
        """ 6.I.4. TEST CASE, BOTH COASTS MUST BE EMPTY FOR BUILDING
            If a sector is occupied on one coast, the other coast can not be used for building.
            Russia may build a unit and has a fleet in St Petersburg(sc). Russia orders the following:
            Russia: Build A St Petersburg(nc)
            Build fails.
        """
        b = BoardBuilder()
        b.inject_centers(b.russia, 2)
        b.fleet(b.st_petersburg_sc, b.russia)
        b.core(b.russia, b.st_petersburg)
        b.build(b.russia, (UnitType.ARMY, b.st_petersburg_nc))
        b.assertBuildCount(0)
        b.builds_adjudicate(self)

    def test_6_i_5(self):
        """ 6.I.5. TEST CASE, BUILDING IN HOME SUPPLY CENTER THAT IS NOT OWNED
            Building a unit is only allowed when supply center is a home supply center and is owned. If not owned,
            build fails.
            Russia captured Berlin in Fall. Left Berlin. Germany can not build in Berlin.
            Germany: Build A Berlin
            Build fails.
        """
        b = BoardBuilder()
        b.inject_centers(b.germany, 1)
        b.berlin.core = b.germany
        b.berlin.owner = b.russia
        b.build(b.germany, (UnitType.ARMY, b.berlin))
        b.assertBuildCount(0)
        b.builds_adjudicate(self)

    def test_6_i_6(self):
        """ 6.I.6. TEST CASE, BUILDING IN OWNED SUPPLY CENTER THAT IS NOT A HOME SUPPLY CENTER
            Building a unit is only allowed when supply center is a home supply center and is owned. If it is not
            a home supply center, the build fails.
            Germany owns Warsaw, Warsaw is empty and Germany may build one unit.
            Germany:
            Build A Warsaw
            Build fails.
        """
        b = BoardBuilder()
        b.inject_centers(b.germany, 1)
        b.warsaw.owner = b.germany
        b.warsaw.core = b.russia
        b.build(b.germany, (UnitType.ARMY, b.warsaw))
        b.assertBuildCount(0)
        b.builds_adjudicate(self)

    def test_6_i_7(self):
        """ 6.I.7. TEST CASE, ONLY ONE BUILD IN A HOME SUPPLY CENTER
            If you may build two units, you can still only build one in a supply center.
            Russia owns Moscow, Moscow is empty and Russia may build two units.
            Russia: Build A Moscow
            Russia: Build A Moscow
            The second build should fail.
        """
        b = BoardBuilder()
        b.inject_centers(b.russia, 2)
        b.core(b.russia, b.moscow)
        b.moscow.core = b.russia
        b.build(b.russia, (UnitType.ARMY, b.moscow), (UnitType.ARMY, b.moscow))
        b.assertBuildCount(1)
        b.builds_adjudicate(self)

    # DEVIATES since currently build orders are unordered
    def test_6_j_1(self):
        """ 6.J.1. TEST CASE, TOO MANY REMOVE ORDERS
            Check how program reacts when someone orders too disbands.
            France has to disband one and has an army in Paris and Picardy.
            France: Remove F Gulf of Lyon
            France: Remove A Picardy
            France: Remove A Paris
            Program should not disband both Paris and Picardy, but should handle it in a different way. See also
            issue 4.D.6. I prefer that the disband orders are handled one by one. According to the preference, the
            removal of the fleet in the Gulf of Lyon fails (no fleet), the removal of the army in Picardy succeeds and
            the removal of the army in Paris fails (too many disbands).
        """
        b = BoardBuilder()
        b.inject_centers(b.france, 1)
        b.army(b.paris, b.france)
        b.army(b.picardy, b.france)
        # technically the order parser will notice that france doesn't own a unit in gulf of lyon so the order 
        # wouldn't reach this point.
        b.disband(b.france, b.gulf_of_lyon, b.picardy, b.paris)
        b.builds_adjudicate(self)
        b.assertBuildCount(-1)

    # NOT APPLICABLE; 6_j_2 through 6_j_11

    # TODO coring tests?