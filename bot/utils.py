none = 'none'

# TODO: this should be in config
players = {
    none,
    'player 1',
}


def get_player(author) -> str:
    for role in author.roles:
        if role in players:
            return role
    return none


def get_scoreboard() -> str:
    # TODO: implement
    return 'pretend this is the scoreboard'
