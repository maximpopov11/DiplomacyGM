from diplomacy.persistence.board import Board

IMPDIP_SERVER_ID = 1201167737163104376
IMPDIP_SERVER_BOT_STATUS_CHANNEL_ID = 1284336328657600572
IMPDIP_SERVER_SUBSTITUTE_TICKET_CHANNEL_ID = 1294689571103309944
IMPDIP_SERVER_SUBSTITUTE_ADVERTISE_CHANNEL_ID = 1201263909622010037
IMPDIP_SERVER_SUBSTITUTE_LOG_CHANNEL_ID = (
    1282421565174059053  # currently a threadchannel (#gm-hangout->'Reputation Tracker')
)

ERROR_COLOUR = "#FF0000"
PARTIAL_ERROR_COLOUR = "#FF7700"


# Capitalization is ignored in all definitions.
# Please only insert lowercase names.
def _is_member(string: str, group: set) -> bool:
    return string.lower() in group


# Discord roles which are allowed access to moderator commands
_mod_roles: set[str] = {
    "executive",
    "admin",
    "moderators",
    "moderator",
}


def is_mod_role(role_name: str) -> bool:
    return _is_member(role_name, _mod_roles)


# Discord roles which are allowed full access to bot commands
_gm_roles: set[str] = {
    "admin",
    "moderator",
    "moderators",
    "gm",
    "heavenly angel",
    "emergency gm",
    "bot manager",
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
_gm_channels: set[str] = {"admin-chat", "bot-spam", "admin-spam"}


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
