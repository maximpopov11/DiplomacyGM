from typing import Callable

from discord.ext import commands

from bot.utils import is_gm, is_gm_channel, get_player_by_role, is_player_channel, get_player_by_channel, is_admin
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.player import Player

def get_player_by_context(ctx: commands.Context, manager: Manager, description: str):
    player = get_player_by_role(ctx.message.author, manager, ctx.guild.id)
    if player:
        if not is_player_channel(player.name, ctx.channel):
            raise PermissionError(f"You cannot {description} as a player outside of your orders channel.")
    else:
        if not is_gm(ctx.message.author):
            raise PermissionError(f"You cannot {description} because you are neither a GM nor a player.")
        player_channel = get_player_by_channel(ctx.channel, manager, ctx.guild.id)
        if player_channel is not None:
            player = player_channel
        elif not is_gm_channel(ctx.channel):
            raise PermissionError(f"You cannot {description} as a GM in a non-GM channel.")
    return player

# adds one extra argument, player, which is None if run by a GM
def player(description: str = "run this command"):
    def player_check(
        function: Callable[[Player | None, commands.Context, Manager], tuple[str, str | None]]
    ) -> Callable[[commands.Context, Manager], tuple[str, str | None]]:
        def f(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
            player = get_player_by_context(ctx, manager, description)
            return function(player, ctx, manager)

        return f

    return player_check


def gm_context_check(ctx: commands.Context, not_gm: str, not_channel):
    if not is_gm(ctx.message.author):
        raise PermissionError(not_gm)

    if not is_gm_channel(ctx.channel):
        raise PermissionError(not_channel)

def gm_perms_check(ctx, description):
    gm_context_check(ctx, f"You cannot {description} because you are not a GM.", f"You cannot {description} in a non-GM channel.")

def admin_perms_check(ctx, description):
    if not is_admin(ctx.message.author):
        raise PermissionError(f"You cannot {description} as you are not an admin")
    if not is_gm_channel(ctx.channel):
        raise PermissionError(f"You cannot {description} in a non-GM channel.")

def gm(description: str = "run this command"):
    def gm_check(
        function: Callable[[commands.Context, Manager], tuple[str, str | None]]
    ) -> Callable[[commands.Context, Manager], tuple[str, str | None]]:

        def f(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
            gm_perms_check(ctx, description)
            return function(ctx, manager)

        return f

    return gm_check

def admin(description: str = "run this command"):
    def admin_check(
        function: Callable[[commands.Context, Manager], tuple[str, str | None]]
    ) -> Callable[[commands.Context, Manager], tuple[str, str | None]]:

        def f(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
            admin_perms_check(ctx, description)
            return function(ctx, manager)

        return f

    return admin_check
