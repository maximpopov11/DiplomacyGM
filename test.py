import main
from diplomacy.map_parser.vector.vector import Parser
import bot.parse_order as order
board = Parser().parse()

test_order = '''.order
F Mogadishu -> Seychelles_Sea
A Baidoa -> Kismayo
A Mareeg -> Galla
F Hobyo -> Dhambalin_Shore'''

order.parse_order(test_order, None, board, 0)

def parse(ord):
    return order.parse_order(ord, None, board, 0)