import lark

class TreeToOrder(lark.Transformer):
    def __init__(self, board):
        super(self).__init__()
        self.board = board

    def province(self, s):
        name = ' '.join(s).strip()
        return name
    
    def unit(self, s):
        #ignore the fleet/army signifier, if exists
        return s[-1]


def lark_parse_order(message: str):#, player_restriction: Player | None, board: Board, board_id: int, useDB: bool=True) -> str:
    with open("bot/orders.ebnf", 'r') as f:
        lang = f.read()
    parser = lark.Lark(lang, start='statement')
    p = parser.parse(message)
    print(p.pretty())
    out = TreeToOrder().transform(p)
    print(out.pretty())
