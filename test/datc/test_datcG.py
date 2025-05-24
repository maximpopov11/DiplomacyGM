import unittest

from diplomacy.persistence.unit import UnitType
from test.utils import BoardBuilder

# These tests are based off https://webdiplomacy.net/doc/DATC_v3_0.html, with 
# https://github.com/diplomacy/diplomacy/blob/master/diplomacy/tests/test_datc.py being used as a reference as well.

# 6.G. TEST CASES, CONVOYING TO ADJACENT PROVINCES
class TestDATC_G(unittest.TestCase):
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
        a_apulia = b.move(b.turkey, UnitType.ARMY, b.apulia, b.rome)
        f_ionian_sea = b.convoy(b.turkey, b.ionian_sea, a_apulia, b.rome)
        f_tyrrhenian_sea = b.convoy(b.italy, b.tyrrhenian_sea, a_apulia, b.rome)

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
