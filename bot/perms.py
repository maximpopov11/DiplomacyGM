from typing import Callable

from discord.ext import commands
from diplomacy.persistence.manager import Manager
from bot.utils import is_gm, is_gm_channel, get_player_by_role, is_player_channel, get_player_by_channel
from diplomacy.persistence.player import Player


# adds one extra argument, player, which is None if run by a GM
def player(discription: str = "run this command"):
    def player_check(
        function: Callable[[Player | None, commands.Context, Manager], tuple[str, str | None]]
    ) -> Callable[[commands.Context, Manager], tuple[str, str | None]]:
        def f(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
            player = get_player_by_role(ctx.message.author, manager, ctx.guild.id)
            if player:
                if not is_player_channel(player.name, ctx.channel):
                    raise PermissionError(f"You cannot {discription} as a player outside of your orders channel.")
            else:
                if not is_gm(ctx.message.author):
                    raise PermissionError(f"You cannot {discription} because you are neither a GM nor a player.")
                player_channel = get_player_by_channel(ctx.channel, manager, ctx.guild.id)
                if player_channel is not None:
                    player = player_channel
                elif not is_gm_channel(ctx.channel):
                    raise PermissionError(f"You cannot {discription} as a GM in a non-GM channel.")
            return function(player, ctx, manager)

        return f

    return player_check


def gm(discription: str = "run this command"):
    def gm_check(
        function: Callable[[commands.Context, Manager], tuple[str, str | None]]
    ) -> Callable[[commands.Context, Manager], tuple[str, str | None]]:

        def f(ctx: commands.Context, manager: Manager) -> tuple[str, str | None]:
            if not is_gm(ctx.message.author):
                raise PermissionError(f"You cannot {discription} because you are not a GM.")

            if not is_gm_channel(ctx.channel):
                raise PermissionError(f"You cannot {discription} in a non-GM channel.")

            return function(ctx, manager)

        return f

    return gm_check
