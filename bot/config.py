import tomllib
import sys
from typing import List, Tuple, Any

with open("config_defaults.toml", "rb") as toml_file:
    _default_toml = tomllib.load(toml_file)

with open("config.toml", "rb") as toml_file:
    _toml = tomllib.load(toml_file)


def merge_toml(main: dict[str, Any], default: dict[str, Any], current_path: str = "") -> Tuple[
    List[str], dict[str, Any]]:
    output = {}
    errors = []
    for key in default:
        if key in main:
            if type(main[key]) is type(default[key]):
                if isinstance(main[key], dict):
                    new_errors, output[key] = merge_toml(main[key], default[key], current_path=key)
                    errors.extend(new_errors)
                else:
                    output[key] = main[key]
            else:
                errors.append(f"{current_path}.")
        else:
            output[key] = default[key]
    return errors, output


toml_errors, all_config = merge_toml(_toml, _default_toml)

# BOT CONFIG
DISCORD_TOKEN = all_config["bot"]["discord_token"]
LOGGING_LEVEL = all_config["bot"]["log_level"]
COMMAND_PREFIX = all_config["bot"]["command_prefix"]

# EXTENSIONS
EXTENSIONS_TO_LOAD_ON_STARTUP = all_config["extensions"]["load_on_startup"]

# DEVELOPMENT SERVER HUB
BOT_DEV_SERVER_ID = all_config["dev_hub"]["id"]
BOT_DEV_UNHANDLED_ERRORS_CHANNEL_ID = all_config["dev_hub"]["unhandled_errors_channel"]

# IMPERIAL DIPLOMACY HUB
IMPDIP_SERVER_ID = all_config["hub"]["id"]
## Channels
IMPDIP_SERVER_BOT_STATUS_CHANNEL_ID = all_config["hub"]["status_channel"]
IMPDIP_SERVER_SUBSTITUTE_TICKET_CHANNEL_ID = all_config["hub"]["substitute_ticket_channel"]
IMPDIP_SERVER_SUBSTITUTE_ADVERTISE_CHANNEL_ID = all_config["hub"]["substitute_advertise_channel"]
IMPDIP_SERVER_SUBSTITUTE_LOG_CHANNEL_ID = all_config["hub"]["substitute_log_channels"]
IMPDIP_SERVER_WINTER_SCOREBOARD_OUTPUT_CHANNEL_ID = all_config["hub"]["winter_scoreboard_output_channels"]
## Roles
IMPDIP_BOT_WIZARD_ROLE = all_config["hub"]["bot_wizard"]

# COLOURS
EMBED_STANDARD_COLOUR = all_config["colours"]["embed_standard"]
PARTIAL_ERROR_COLOUR = all_config["colours"]["embed_partial_success"]
ERROR_COLOUR = all_config["colours"]["embed_error"]

# TODO: move to config_defaults.toml if applicable or elsewhere
color_options = {"standard", "dark", "pink", "blue", "kingdoms", "empires"}

# INKSCAPE
SIMULATRANEOUS_SVG_EXPORT_LIMIT = all_config["inkscape"]["simultaneous_svg_exports_limit"]

class ConfigException(Exception):
    pass


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
    "gm team",
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
