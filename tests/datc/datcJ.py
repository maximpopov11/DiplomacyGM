import unittest

from diplomacy.persistence.order import (
    Move,
    ConvoyTransport,
    Support,
)
from diplomacy.persistence.unit import UnitType
from tests.utils import BoardBuilder

# These tests are based off https://webdiplomacy.net/doc/DATC_v3_0.html, with 
# https://github.com/diplomacy/diplomacy/blob/master/diplomacy/tests/test_datc.py being used as a reference as well.

# 6.J. TEST CASES, CIVIL DISORDER AND DISBANDS
class TestDATC_J(unittest.TestCase):
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

