import unittest

from diplomacy.persistence.order import (
    Support,
)
from diplomacy.persistence.unit import UnitType
from test.utils import BoardBuilder

# These tests are based off https://webdiplomacy.net/doc/DATC_v3_0.html, with 
# https://github.com/diplomacy/diplomacy/blob/master/diplomacy/tests/test_datc.py being used as a reference as well.

# 6.A. TEST CASES, BASIC CHECKS
class TestDATC_A(unittest.TestCase):

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

    def test_6_a_5(self):
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
        b.assertSuccess(f_london, a_liverpool)
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
        order = Support(b.trieste_c, b.trieste_c)
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
