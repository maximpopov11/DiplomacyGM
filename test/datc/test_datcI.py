import unittest

from diplomacy.persistence.unit import UnitType
from test.utils import BoardBuilder

# These tests are based off https://webdiplomacy.net/doc/DATC_v3_0.html, with 
# https://github.com/diplomacy/diplomacy/blob/master/diplomacy/tests/test_datc.py being used as a reference as well.

# 6.I. TEST CASES, BUILDING
class TestDATC_I(unittest.TestCase):
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
        b.player_core(b.germany, b.warsaw, b.kiel, b.munich)
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
        b.player_core(b.russia, b.moscow)
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
        b.player_core(b.germany, b.berlin)
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
        b.player_core(b.russia, b.st_petersburg)
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
        b.player_core(b.russia, b.moscow)
        b.moscow.core = b.russia
        b.build(b.russia, (UnitType.ARMY, b.moscow), (UnitType.ARMY, b.moscow))
        b.assertBuildCount(1)
        b.builds_adjudicate(self)
