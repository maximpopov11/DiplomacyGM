from discord.ext import commands

from bot.config import gm_roles, gm_channels, player_channel_suffix
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.player import Player


def is_gm(author: commands.Context.author) -> bool:
    for role in author.roles:
        if role.name in gm_roles:
            return True
    return False


def is_gm_channel(channel: commands.Context.channel) -> bool:
    return channel.name in gm_channels


def get_player(author: commands.Context.author, manager: Manager, server_id: int) -> Player | None:
    for role in author.roles:
        for player in manager.get_board(server_id).players:
            if player.name == role.name:
                return player
    return None


def is_player_channel(player_role: str, channel: commands.Context.channel) -> bool:
    player_channel = player_role.lower() + player_channel_suffix
    return player_channel == channel.name
