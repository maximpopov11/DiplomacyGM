from typing import Callable

from discord.ext import commands
from diplomacy.persistence.manager import Manager
from bot.utils import is_gm, is_gm_channel, get_player_by_role, is_player_channel
from diplomacy.persistence.player import Player


# adds one extra argument, player, which is None if run by a GM 
def player(function: Callable[[Player | None, commands.Context, Manager], tuple[str, str | None]], discription: str="run this command") -> Callable[[commands.Context, Manager], tuple[str, str | None]]:
    
    def f(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
        if is_gm(ctx.author):
            if not is_gm_channel(ctx.channel):
                raise PermissionError(f"You cannot {discription} as a GM in a non-GM channel.")
            player = None
        else:
            player = get_player_by_role(ctx.channel, manager, ctx.guild.id)
            if player is None:
                raise PermissionError(f"You cannot {discription} because you are neither a GM nor a player.")
            if not is_player_channel(player.name, ctx.channel):
                raise PermissionError(f"You cannot {discription} as a player outside of your orders channel.")

        return function(player, ctx, manager)
    
    return f

def gm(function: Callable[[commands.Context, Manager], tuple[str, str | None]], discription: str="run this command") -> Callable[[commands.Context, Manager], tuple[str, str | None]]:

    def f(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
        if not is_gm(ctx.message.author):
            raise PermissionError(f"You cannot {discription} because you are not a GM.")

        if not is_gm_channel(ctx.channel):
            raise PermissionError(f"You cannot {discription} in a non-GM channel.")

        return function(ctx, manager)
    
    return f