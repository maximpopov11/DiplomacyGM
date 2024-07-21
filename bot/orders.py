def parse(message: str) -> str:
    orders = str.splitlines(message)
    invalid = []
    for order in orders:
        try:
            _parse_order(order)
        except AssertionError:
            invalid.append(order)

    if invalid:
        response = 'The following orders were invalid:'
        for order in invalid:
            response += '\n' + order
    else:
        response = 'Orders validated successfully.'

    return response


hold = 'hold'
move = 'move'
support = 'support'
convoy = 'convoy'


order_dict = {
    hold: ['h', 'hold', 'holds'],
    move: ['-', '->', 'to', 'm', 'move', 'moves'],
    support: ['s', 'support', 'supports'],
    convoy: ['c', 'convoy', 'convoys'],
}


def _parse_order(order: str) -> str:
    # TODO: implement order class
    # TODO: implement this func: assert correct # of parts and legal values of parts for assertion error to trickle down
    return ''
