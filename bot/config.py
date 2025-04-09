ERROR_COLOUR = "#FF0000"
PARTIAL_ERROR_COLOUR = "#FF7700"


# Capitalization is ignored in all definitions.
# Please only insert lowercase names.
def _is_member(string: str, group: set) -> bool:
    return string.lower() in group


# Discord roles which are allowed full access to bot commands
_gm_roles: set[str] = {
    "admin",
    "gm",
    "heavenly angel",
    "emergency gm",
}


def is_gm_role(role: str) -> bool:
    return _is_member(role, _gm_roles)

# Player roles which are allowed player to bot commands
_player_roles: set[str] = {
    "player",
}

def is_player_role(role: str) -> bool:
    return _is_member(role, _player_roles)


# Discord categories in which GM channels must be
# (so that you can't create a fake GM channel with the right name)
_gm_categories: set[str] = {
    "gm channels",
}


def is_gm_category(category: str) -> bool:
    return _is_member(category, _gm_categories)


# Discord channels in which GMs are allowed to use non-public commands (e.g. adjudication)
_gm_channels: set[str] = {"admin-chat"}


def is_gm_channel(channel: str) -> bool:
    return _is_member(channel, _gm_channels)


# Discord categories in which player channels must be
# (so that you can't create a fake player channel with the right name)
_player_categories: set[str] = {
    "orders",
}


def is_player_category(category: str) -> bool:
    return _is_member(category, _player_categories)


# Channel suffix for player orders channels.
# E.g. if the player is "france" and the suffix is "-orders", the channel is "france-orders"
player_channel_suffix: str = "-orders"

# Temporary bumbleship holds until the server restarts or until you fish too much
temporary_bumbles: set[str] = set()


def is_bumble(name: str) -> bool:
    return name == "_bumble" or name in temporary_bumbles
