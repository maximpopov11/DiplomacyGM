import unittest

from diplomacy.persistence.unit import UnitType
from test.utils import BoardBuilder

# These tests are based off https://webdiplomacy.net/doc/DATC_v3_0.html, with 
# https://github.com/diplomacy/diplomacy/blob/master/diplomacy/tests/test_datc.py being used as a reference as well.

# 6.E. TEST CASES, HEAD-TO-HEAD BATTLES AND BELEAGUERED GARRISON
class TestDATC_E(unittest.TestCase):
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
        f_kiel = b.move(b.germany, UnitType.FLEET, b.kiel_c, b.berlin_c)
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

        b.assertSuccess(f_holland, f_yorkshire, f_skagerrak, f_north_sea, f_norway)
        b.assertFail(f_helgoland_bight)
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
