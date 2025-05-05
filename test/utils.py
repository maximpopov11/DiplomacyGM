from diplomacy.persistence.board import Board
from diplomacy.persistence.order import (
    Core,
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

import unittest

# Allows for specifying units, uses the classic diplomacy board as that is used by DATC 
# Only implements the subset of adjacencies necessary to run the DATC tests as of now
class BoardBuilder():
    def __init__(self, season: str = "Spring"):
        self.board = Board(
            players=set(),
            provinces=set(),
            units=set(),
            phase=Phase(f"{season} 1901", None, None),
            data=None,
            datafile=None,
            fow=False
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
        self.holland = self._land("Holland", sc=True)
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

        self.liverpool.adjacent = set([self.wales, self.irish_sea, self.north_atlantic_ocean, self.clyde, self.edinburgh, self.yorkshire])
        self.liverpool_c.adjacent_seas = set([self.irish_sea, self.north_atlantic_ocean])
        self.irish_sea.adjacent = set([self.liverpool, self.wales, self.english_channel, self.mid_atlantic_ocean, self.north_atlantic_ocean])
        self.mid_atlantic_ocean.adjacent = set([self.irish_sea, self.english_channel, self.brest, self.gascony, self.spain, self.portugal, self.western_mediterranean, self.north_africa, self.north_atlantic_ocean])
        self.north_sea.adjacent = set([self.yorkshire, self.edinburgh, self.norwegian_sea, self.norway, self.skagerrak, self.denmark, self.helgoland_bight, self.holland, self.belgium, self.english_channel, self.london])
        self.yorkshire.adjacent = set([self.north_sea, self.london, self.wales, self.liverpool, self.edinburgh])
        self.yorkshire_c.adjacent_seas = set([self.north_sea])
        self.london.adjacent = set([self.yorkshire, self.north_sea, self.english_channel, self.wales])
        self.london_c.adjacent_seas = set([self.north_sea, self.english_channel])
        self.edinburgh.adjacent = set([self.norwegian_sea, self.north_sea, self.yorkshire, self.liverpool, self.clyde])
        self.edinburgh_c.adjacent_seas = set([self.norwegian_sea, self.north_sea])
        self.english_channel.adjacent = set([self.picardy, self.brest, self.mid_atlantic_ocean, self.irish_sea, self.wales, self.london, self.north_sea, self.belgium])
        self.wales.adjacent = set([self.london, self.english_channel, self.irish_sea, self.liverpool, self.yorkshire])
        self.wales_c.adjacent_seas = set([self.english_channel, self.irish_sea])
        self.north_atlantic_ocean.adjacent = set([self.norwegian_sea, self.clyde, self.liverpool, self.irish_sea, self.mid_atlantic_ocean])
        self.norwegian_sea.adjacent = set([self.north_atlantic_ocean, self.edinburgh, self.clyde, self.north_sea, self.barents_sea, self.st_petersburg, self.norway])
        self.clyde.adjacent = set([self.north_atlantic_ocean, self.norwegian_sea, self.edinburgh, self.liverpool])
        self.clyde_c.adjacent_seas = set([self.north_atlantic_ocean, self.norwegian_sea])

        self.north_africa.adjacent = set([self.mid_atlantic_ocean, self.western_mediterranean, self.tunis])

        self.picardy.adjacent = set([self.belgium, self.burgundy, self.paris, self.brest, self.english_channel])
        self.picardy_c.adjacent_seas = set([self.english_channel])

        self.kiel.adjacent = set([self.munich, self.ruhr, self.holland, self.helgoland_bight, self.denmark, self.baltic_sea, self.berlin])
        self.kiel_c.adjacent_seas = set([self.baltic_sea, self.helgoland_bight])
        self.munich.adjacent = set([self.kiel, self.berlin, self.silesia, self.bohemia, self.tyrolia, self.burgundy])
        self.berlin.adjacent = set([self.kiel, self.baltic_sea, self.prussia, self.silesia, self.munich])
        self.berlin_c.adjacent_seas = set([self.baltic_sea])
        self.prussia.adjacent = set([self.berlin, self.baltic_sea, self.livonia, self.silesia, self.warsaw])
        self.prussia_c.adjacent_seas = set([self.baltic_sea])
        self.baltic_sea.adjacent = set([self.berlin, self.kiel, self.denmark, self.sweden, self.gulf_of_bothnia, self.livonia, self.prussia])
        self.silesia.adjacent = set([self.berlin, self.prussia, self.warsaw, self.galicia, self.bohemia, self.munich])
        self.bohemia.adjacent = set([self.munich, self.silesia, self.galicia, self.venice, self.tyrolia])

        self.sweden.adjacent = set([self.gulf_of_bothnia, self.baltic_sea, self.denmark, self.skagerrak, self.norway, self.finland])
        self.sweden_c.adjacent_seas = set([self.baltic_sea, self.skagerrak, self.gulf_of_bothnia])
        self.finland.adjacent = set([self.st_petersburg, self.livonia, self.baltic_sea, self.sweden, self.norway])
        self.finland_c.adjacent_seas = set([self.gulf_of_bothnia])
        self.denmark.adjacent = set([self.baltic_sea, self.kiel, self.helgoland_bight, self.north_sea, self.skagerrak, self.sweden])
        self.denmark_c.adjacent_seas = set([self.baltic_sea, self.helgoland_bight, self.north_sea, self.skagerrak])
        self.norway.adjacent = set([self.north_sea, self.norwegian_sea, self.barents_sea, self.st_petersburg, self.finland, self.sweden, self.skagerrak])
        self.norway_c.adjacent_seas = set([self.north_sea, self.norwegian_sea, self.barents_sea, self.skagerrak])

        self.belgium.adjacent = set([self.north_sea, self.holland, self.ruhr, self.burgundy, self.picardy, self.english_channel])
        self.belgium_c.adjacent_seas = set([self.north_sea, self.english_channel])
        self.holland.adjacent = set([self.north_sea, self.helgoland_bight, self.kiel, self.ruhr, self.belgium])
        self.holland_c.adjacent_seas = set([self.north_sea, self.helgoland_bight])
        self.helgoland_bight.adjacent = set([self.kiel, self.holland, self.north_sea, self.denmark])
        self.skagerrak.adjacent = set([self.north_sea, self.norway, self.sweden, self.denmark])
        self.ruhr.adjacent = set([self.belgium, self.holland, self.kiel, self.munich, self.burgundy])

        # no tuscany, piedmont
        self.venice.adjacent = set([self.tyrolia, self.trieste, self.adriatic_sea, self.apulia, self.naples, self.rome])

        self.trieste.adjacent = set([self.vienna, self.budapest, self.serbia, self.albania, self.adriatic_sea, self.venice, self.tyrolia])
        self.trieste_c.adjacent_seas = set([self.adriatic_sea])
        # no pedimont
        self.tyrolia.adjacent = set([self.trieste, self.venice, self.munich, self.bohemia, self.venice])
        self.vienna.adjacent = set([self.tyrolia, self.bohemia, self.galicia, self.budapest, self.trieste])
        # no tuscany
        self.rome.adjacent = set([self.venice, self.apulia, self.naples, self.tyrrhenian_sea])
        self.apulia.adjacent = set([self.rome, self.venice, self.adriatic_sea, self.ionian_sea, self.naples])
        self.apulia_c.adjacent_seas = set([self.ionian_sea, self.adriatic_sea])
        self.naples.adjacent = set([self.tyrrhenian_sea, self.rome, self.apulia, self.ionian_sea])
        self.tunis.adjacent = set([self.tyrrhenian_sea, self.ionian_sea, self.north_africa, self.western_mediterranean])

        self.greece.adjacent = set([self.serbia, self.bulgaria, self.aegean_sea, self.ionian_sea, self.albania])
        self.greece_c.adjacent_seas = set([self.aegean_sea, self.ionian_sea])
        self.albania.adjacent = set([self.greece, self.ionian_sea, self.adriatic_sea, self.trieste, self.serbia])
        self.albania_c.adjacent_seas = set([self.adriatic_sea, self.ionian_sea])

        self.rome_c.adjacent_seas = set([self.tyrrhenian_sea])
        self.venice_c.adjacent_seas = set([self.adriatic_sea])
        self.naples_c.adjacent_seas = set([self.tyrrhenian_sea, self.ionian_sea])
        self.tunis_c.adjacent_seas = set([self.tyrrhenian_sea, self.ionian_sea, self.western_mediterranean])

        self.spain.adjacent = set([self.gascony, self.marseilles, self.gulf_of_lyon, self.western_mediterranean, self.mid_atlantic_ocean, self.portugal])
        self.gascony.adjacent = set([self.marseilles, self.spain, self.mid_atlantic_ocean, self.brest, self.paris, self.burgundy])
        self.burgundy.adjacent = set([self.gascony, self.paris, self.picardy, self.belgium, self.ruhr, self.munich, self.marseilles])
        self.western_mediterranean.adjacent = set([self.mid_atlantic_ocean, self.spain, self.gulf_of_lyon, self.tyrrhenian_sea, self.tunis, self.north_africa])
        # no piedmont
        self.marseilles.adjacent = set([self.gascony, self.burgundy, self.gulf_of_lyon, self.spain])
        # no piedmont, tuscany
        self.gulf_of_lyon.adjacent = set([self.marseilles, self.tyrrhenian_sea, self.western_mediterranean, self.spain])
        self.brest.adjacent = set([self.picardy, self.paris, self.gascony, self.mid_atlantic_ocean, self.english_channel])
        self.brest_c.adjacent_seas = set([self.english_channel, self.mid_atlantic_ocean])
        self.paris.adjacent = set([self.brest, self.picardy, self.burgundy, self.gascony])

        self.spain_nc.adjacent_seas = set([self.mid_atlantic_ocean])
        self.spain_sc.adjacent_seas = set([self.mid_atlantic_ocean, self.western_mediterranean, self.gulf_of_lyon])
        self.gascony_c.adjacent_seas = set([self.mid_atlantic_ocean])
        self.portugal.adjacent = set([self.mid_atlantic_ocean, self.spain])
        self.portugal_c.adjacent_seas = set([self.mid_atlantic_ocean])
        # no piedmont
        self.marseilles_c.adjacent_seas = set([self.gulf_of_lyon, self.spain, self.gascony, self.burgundy])

        self.gulf_of_bothnia.adjacent = set([self.st_petersburg, self.livonia, self.baltic_sea, self.sweden, self.finland])
        self.livonia.adjacent = set([self.gulf_of_bothnia, self.st_petersburg, self.moscow, self.warsaw, self.prussia, self.baltic_sea])
        self.livonia_c.adjacent_seas = set([self.gulf_of_bothnia, self.baltic_sea])
        self.barents_sea.adjacent = set([self.st_petersburg, self.norway, self.norwegian_sea])
        self.st_petersburg.adjacent = set([self.gulf_of_bothnia, self.finland, self.norway, self.barents_sea, self.moscow, self.livonia])
        self.st_petersburg_nc.adjacent_seas = set([self.barents_sea])
        self.st_petersburg_sc.adjacent_seas = set([self.gulf_of_bothnia])
        # no ukraine
        self.warsaw.adjacent = set([self.prussia, self.liverpool, self.moscow, self.galicia, self.silesia])

        self.bulgaria.adjacent = set([self.aegean_sea, self.greece, self.serbia, self.rumania, self.black_sea, self.constantinople])
        self.bulgaria_ec.adjacent_seas = set([self.black_sea])
        self.bulgaria_sc.adjacent_seas = set([self.aegean_sea])
        self.serbia.adjacent = set([self.bulgaria, self.greece, self.albania, self.trieste, self.budapest, self.rumania])
        # no tuscany
        self.tyrrhenian_sea.adjacent = set([self.rome, self.naples, self.ionian_sea, self.tunis, self.western_mediterranean, self.gulf_of_lyon])
        self.aegean_sea.adjacent = set([self.bulgaria, self.constantinople, self.smyrna, self.eastern_mediterranean, self.ionian_sea, self.greece])
        self.black_sea.adjacent = set([self.bulgaria, self.rumania, self.sevastopol, self.armenia, self.ankara, self.constantinople])
        self.ionian_sea.adjacent = set([self.naples, self.apulia, self.adriatic_sea, self.albania, self.greece, self.aegean_sea, self.eastern_mediterranean, self.tunis, self.tyrrhenian_sea])
        self.adriatic_sea.adjacent = set([self.trieste, self.albania, self.ionian_sea, self.apulia, self.venice])
        self.constantinople.adjacent = set([self.ankara, self.smyrna, self.aegean_sea, self.bulgaria, self.black_sea])
        self.constantinople_c.adjacent_seas = set([self.aegean_sea, self.black_sea])
        self.ankara.adjacent = set([self.constantinople, self.black_sea, self.armenia, self.smyrna])
        self.ankara_c.adjacent_seas = set([self.black_sea])
        # no syria
        self.smyrna.adjacent = set([self.aegean_sea, self.constantinople, self.ankara, self.armenia, self.eastern_mediterranean])
        # no syria
        self.eastern_mediterranean.adjacent = set([self.ionian_sea, self.aegean_sea, self.smyrna])
        # no syria
        self.armenia.adjacent = set([self.ankara, self.sevastopol, self.smyrna])
        # no ukraine
        self.rumania.adjacent = set([self.black_sea, self.bulgaria, self.serbia, self.budapest, self.galicia, self.sevastopol])
        self.budapest.adjacent = set([self.rumania, self.serbia, self.trieste, self.vienna, self.galicia])
        # no ukraine
        self.galicia.adjacent = set([self.vienna, self.bohemia, self.silesia, self.warsaw, self.rumania, self.budapest])
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

    def core(self, player: Player, type: UnitType, place: Location) -> Unit:
        if (type == UnitType.FLEET):
            unit = self.fleet(place, player)
        else:
            unit = self.army(place, player)

        order = Core()
        unit.order = order

        return unit

    def convoy(self, player: Player, place: Location, source: Unit, to: Location) -> Unit:
        unit = self.fleet(place, player)
        
        order = ConvoyTransport(source.location(), to)
        unit.order = order

        return unit
    
    def supportMove(self, player: Player, type: UnitType, place: Location, source: Unit, to: Location) -> Unit:
        if (type == UnitType.FLEET):
            unit = self.fleet(place, player)
        else:
            unit = self.army(place, player)

        order = Support(source.location(), to)
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

        order = Support(source.location(), source.location())
        unit.order = order

        return unit
    
    def retreat(self, unit: Unit, place: Location):
        unit.order = RetreatMove(place)
        pass

    def build(self, player: Player, *places: tuple[UnitType, Location]):
        player.build_orders |= set([Build(info[1], info[0]) for info in places])

    def disband(self, player: Player, *places: Location):
        player.build_orders |= set([Disband(place) for place in places])

    def player_core(self, player: Player, *places: Province):
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
