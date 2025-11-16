from functools import wraps
from typing import Any, Awaitable, Callable

from discord import HTTPException
from discord.ext import commands

from bot.config import IMPDIP_SERVER_ID
from bot.utils import (
    is_gm,
    is_gm_channel,
    get_player_by_role,
    is_moderator,
    is_player_channel,
    get_player_by_channel,
    is_superuser,
)
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.player import Player

manager = Manager()


class CommandPermissionError(commands.CheckFailure):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def get_player_by_context(ctx: commands.Context):
    # FIXME cleaner way of doing this
    board = manager.get_board(ctx.guild.id)
    # return if in order channel
    weak_channel_checking = "weak channel checking" in board.data.get("flags", [])
    if board.fow or weak_channel_checking:
        player = get_player_by_channel(
            ctx.channel, manager, ctx.guild.id, ignore_category=weak_channel_checking
        )
    else:
        player = get_player_by_role(ctx.message.author, manager, ctx.guild.id)

    return player


def require_player_by_context(ctx: commands.Context, description: str):
    # FIXME cleaner way of doing this
    board = manager.get_board(ctx.guild.id)
    # return if in order channel
    weak_channel_checking = "weak channel checking" in board.data.get("flags", [])
    if board.fow or weak_channel_checking:
        player = get_player_by_channel(
            ctx.channel, manager, ctx.guild.id, ignore_category=weak_channel_checking
        )
        if player:
            return player
    else:
        player = get_player_by_role(ctx.message.author, manager, ctx.guild.id)

    if player:
        if not is_player_channel(player.name, ctx.channel):
            raise CommandPermissionError(
                f"You cannot {description} as a player outside of your orders channel."
            )
    else:
        if not is_gm(ctx.message.author):
            raise CommandPermissionError(
                f"You cannot {description} because you are neither a GM nor a player."
            )
        player_channel = get_player_by_channel(ctx.channel, manager, ctx.guild.id)
        if player_channel is not None:
            player = player_channel
        elif not is_gm_channel(ctx.channel):
            raise CommandPermissionError(
                f"You cannot {description} as a GM in non-player and non-GM channels."
            )
    return player


# adds one extra argument, player in a player's channel, which is None if run by a GM in a GM channel
def player(description: str = "run this command"):
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(self, ctx: commands.Context, player: Player | None):
            # manager should live on bot or cog; here I assume cog
            player = require_player_by_context(ctx, description)

            # Inject the resolved player into the *real* function call
            return await func(self, ctx, player)

        return wrapper

    return decorator


async def assert_mod_only(
    ctx: commands.Context, description: str = "run this command"
) -> bool:
    _hub = ctx.bot.get_guild(IMPDIP_SERVER_ID)
    if not _hub:
        raise CommandPermissionError(
            "Cannot fetch the Imperial Diplomacy Hub server moderator permissions."
        )

    _member = _hub.get_member(ctx.author.id)
    if not _member:
        raise CommandPermissionError(
            f"You cannot {description} as you could not be found as a member of the Imperial Diplomacy Hub server."
        )

    if not is_moderator(_member):
        raise CommandPermissionError(
            f"You cannot {description} as you are not a moderator on the Imperial Diplomacy Hub server."
        )

    if not is_moderator(ctx.author):
        raise CommandPermissionError(
            f"You cannot {description} as you are not a moderator on the current server."
        )

    return True


def mod_only(description: str = "run this command"):
    return commands.check(lambda ctx: assert_mod_only(ctx, description))


def assert_gm_only(
    ctx: commands.Context, description: str = "run this command", non_gm_alt: str = ""
):
    if not is_gm(ctx.message.author):
        raise CommandPermissionError(
            non_gm_alt or f"You cannot {description} because you are not a GM."
        )
    elif not is_gm_channel(ctx.channel):
        raise CommandPermissionError(f"You cannot {description} in a non-GM channel.")
    else:
        return True


def gm_only(description: str = "run this command"):
    return commands.check(lambda ctx: assert_gm_only(ctx, description))


def assert_superuser_only(ctx: commands.Context, description: str = "run this command"):
    if not is_superuser(ctx.message.author):
        raise CommandPermissionError(
            f"You cannot {description} as you are not an superuser"
        )
    else:
        return True


def superuser_only(description: str = "run this command"):
    return commands.check(lambda ctx: assert_superuser_only(ctx, description))
