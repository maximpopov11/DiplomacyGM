from typing import Optional

from discord.ext import commands

from config import *
from diplomacy.persistence.adjudicator import Adjudicator
from diplomacy.player import Player


def is_gm(author: commands.Context.author) -> bool:
    for role in author.roles:
        if role.name in gms:
            return True
    return False


def is_gm_channel(channel: commands.Context.channel) -> bool:
    return channel.name in gm_channels


def is_player(author: commands.Context.author) -> bool:
    return get_player(author) is not None


def get_player(author: commands.Context.author, adjudicator: Adjudicator) -> Optional[Player]:
    for role in author.roles:
        player = adjudicator.get_player(role.name)
        if player is not None:
            return player
    return None


def is_player_channel(player_role: str, channel: commands.Context.channel) -> bool:
    player_channel = player_role.lower() + player_channel_suffix
    return player_channel == channel.name
