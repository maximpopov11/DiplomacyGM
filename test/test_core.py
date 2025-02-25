import unittest

from diplomacy.persistence.unit import UnitType
from test.utils import BoardBuilder

class TestCore(unittest.TestCase):
    def test_core_1(self):
        """ 
            Coring should fail for non-SCs.
            Germany: A Rumania Cores
            Rumania shouldn't be half-cored by Germany.
        """
        b = BoardBuilder()
        a_rumania = b.core(b.germany, UnitType.ARMY, b.rumania)

        b.assertIllegal(a_rumania)
        b.moves_adjudicate(self)
        self.assertFalse(b.rumania.half_core == b.germany, "Rumania shouldn't be cored")

    def test_core_2(self):
        """ 
            Coring should fail for not owned provinces.
            Germany doesn't own Holland.
            Germany: A Holland Cores
            Holland shouldn't be half-cored by Germany.
        """
        b = BoardBuilder()
        a_holland = b.core(b.germany, UnitType.ARMY, b.holland)

        b.assertIllegal(a_holland)
        b.moves_adjudicate(self)
        self.assertFalse(b.holland.half_core == b.germany, "Holland shouldn't be cored")

    def test_core_3(self):
        """ 
            Coring should turn empty cores into half cores.
            Germany owns Holland.
            Germany: A Holland Cores
            Holland should be half-cored by Germany.
        """
        b = BoardBuilder()
        b.holland.owner = b.germany
        a_holland = b.core(b.germany, UnitType.ARMY, b.holland)

        b.assertSuccess(a_holland)
        b.moves_adjudicate(self)
        print(b.holland.half_core)
        self.assertTrue(b.holland.half_core == b.germany, "Holland should be half-cored")

    def test_core_4(self):
        """ 
            Coring should turn half cores into full cores.
            Germany owns Holland.
            Germany: A Holland Cores
            Holland should be cored by Germany.
        """
        b = BoardBuilder()
        b.holland.owner = b.germany
        b.holland.half_core = b.germany
        a_holland = b.core(b.germany, UnitType.ARMY, b.holland)

        b.assertSuccess(a_holland)
        b.moves_adjudicate(self)
        print(b.holland.half_core)
        self.assertTrue(b.holland.core == b.germany, "Holland should be cored")

    def test_core_5(self):
        """ 
            Coring should failed when the coring unit is attacked.
            Germany owns Holland.
            Germany: A Holland Cores
            France: A Belgium - Holland
            Holland shouldn't be half-cored by Germany.
        """
        b = BoardBuilder()
        b.holland.owner = b.germany
        b.holland.half_core = b.germany
        a_holland = b.core(b.germany, UnitType.ARMY, b.holland)
        a_belgium = b.move(b.france, UnitType.ARMY, b.belgium, b.holland)

        b.assertFail(a_holland, a_belgium)
        b.assertNotIllegal(a_holland, a_belgium)
        b.moves_adjudicate(self)
        
        self.assertFalse(b.holland.core == b.germany, "Holland shouldn't be cored")

    def test_core_5(self):
        """ 
            Coring should failed when the attacking unit is of the same nationality.
            Germany owns Holland.
            Germany: A Holland Cores
            Germany: A Belgium - Holland
            Holland shouldn't be half-cored by Germany.
        """
        b = BoardBuilder()
        b.holland.owner = b.germany
        b.holland.half_core = b.germany
        a_holland = b.core(b.germany, UnitType.ARMY, b.holland)
        a_belgium = b.move(b.germany, UnitType.ARMY, b.belgium, b.holland)

        b.assertFail(a_holland, a_belgium)
        b.assertNotIllegal(a_holland, a_belgium)
        b.moves_adjudicate(self)
        
        self.assertFalse(b.holland.core == b.germany, "Holland shouldn't be half-cored")

    def test_core_6(self):
        """ 
            Coring should fail when attacked by convoy.
            Germany owns Holland.
            Germany: A Holland Cores
            England: A London - Holland
            England: F North Sea Convoys A London - Holland
            Holland should be half-cored by Germany.
        """
        b = BoardBuilder()
        b.holland.owner = b.germany
        b.holland.half_core = b.germany
        a_holland = b.core(b.germany, UnitType.ARMY, b.holland)
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.holland)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.holland)

        b.assertFail(a_holland, a_london)
        b.assertNotIllegal(a_holland, f_north_sea, a_london)
        b.moves_adjudicate(self)
        
        self.assertFalse(b.holland.core == b.germany, "Holland shouldn't be half-cored")

    def test_core_7(self):
        """ 
            Coring should failed when attacked by convoy of the same nationality.
            Germany owns Holland.
            Germany: A Holland Cores
            Germany: A London - Holland
            England: F North Sea Convoys A London - Holland
            Holland should be half-cored by Germany.
        """
        b = BoardBuilder()
        b.holland.owner = b.germany
        b.holland.half_core = b.germany
        a_holland = b.core(b.germany, UnitType.ARMY, b.holland)
        a_london = b.move(b.germany, UnitType.ARMY, b.london, b.holland)
        f_north_sea = b.convoy(b.england, b.north_sea, a_london, b.holland)

        b.assertFail(a_holland, a_london)
        b.assertNotIllegal(a_holland, f_north_sea, a_london)
        b.moves_adjudicate(self)
        
        self.assertFalse(b.holland.core == b.germany, "Holland shouldn't be half-cored")


    def test_core_8(self):
        """ 
            Coring should succeed when only attacked by a disrupted convoy.
            Germany owns Holland.
            Germany: A Holland Cores
            England: A London - Holland
            Holland should be half-cored by Germany.
        """
        b = BoardBuilder()
        b.holland.owner = b.germany
        b.holland.half_core = b.germany
        a_holland = b.core(b.germany, UnitType.ARMY, b.holland)
        a_london = b.move(b.england, UnitType.ARMY, b.london, b.holland)

        b.assertSuccess(a_holland)
        b.moves_adjudicate(self)
        
        self.assertTrue(b.holland.core == b.germany, "Holland should be half-cored")