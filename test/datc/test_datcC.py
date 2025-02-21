import unittest

from diplomacy.persistence.unit import UnitType
from test.utils import BoardBuilder

# These tests are based off https://webdiplomacy.net/doc/DATC_v3_0.html, with 
# https://github.com/diplomacy/diplomacy/blob/master/diplomacy/tests/test_datc.py being used as a reference as well.

# 6.C. TEST CASES, CIRCULAR MOVEMENT
class TestDATC_C(unittest.TestCase):
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