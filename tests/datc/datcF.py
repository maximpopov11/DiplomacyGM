import unittest

from diplomacy.persistence.order import Support
from diplomacy.persistence.unit import UnitType
from tests.utils import BoardBuilder

# These tests are based off https://webdiplomacy.net/doc/DATC_v3_0.html, with 
# https://github.com/diplomacy/diplomacy/blob/master/diplomacy/tests/test_datc.py being used as a reference as well.

# 6.F. TEST CASES, CONVOYS
class TestDATC_F(unittest.TestCase):
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
