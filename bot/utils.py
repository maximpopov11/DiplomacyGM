import datetime
import asyncio
import io
import logging
import os
import time
import zipfile
import discord
from typing import List, Tuple
from discord import Embed, Colour, Guild, Message
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands import Context

from bot import config

from diplomacy.adjudicator.utils import svg_to_png, png_to_jpg
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType
from logging import getLogger
logger = getLogger(__name__)

whitespace_dict = {
    "_",
}

_north_coast = "nc"
_south_coast = "sc"
_east_coast = "ec"
_west_coast = "wc"

coast_dict = {
    _north_coast: ["nc", "north coast", "(nc)"],
    _south_coast: ["sc", "south coast", "(sc)"],
    _east_coast: ["ec", "east coast", "(ec)"],
    _west_coast: ["wc", "west coast", "(wc)"],
}

_army = "army"
_fleet = "fleet"

unit_dict = {
    _army: ["a", "army", "cannon"],
    _fleet: ["f", "fleet", "boat", "ship"],
}

discord_message_limit = 2000
discord_file_limit = 10 * (2**20)
discord_embed_description_limit = 4096
discord_embed_total_limit = 6000

def is_admin(author: commands.Context.author) -> bool:
    return author.id in [
        1217203346511761428,    # eebop
        332252245259190274,     # Icecream Guy
        169995316680982528,     # Bumble
        450636420558618625,     # Flare
        490633966974533640,     # Elle
    ]


def is_gm(author: commands.Context.author) -> bool:
    for role in author.roles:
        if config.is_gm_role(role.name):
            return True
    return False


def is_gm_channel(channel: commands.Context.channel) -> bool:
    return config.is_gm_channel(channel.name) and config.is_gm_category(channel.category.name)


def get_player_by_role(author: commands.Context.author, manager: Manager, server_id: int) -> Player | None:
    for role in author.roles:
        for player in manager.get_board(server_id).players:
            if player.name == role.name:
                return player
    return None

def get_role_by_player(player: Player, roles: Guild.roles) -> discord.Role | None:
    for role in roles:
        if role.name == player.name:
            return role
    return None


def get_player_by_channel(channel: commands.Context.channel, manager: Manager, server_id: int) -> Player | None:
    name = channel.name
    if not name.endswith(config.player_channel_suffix) or not config.is_player_category(channel.category.name):
        return None
    name = name[: -(len(config.player_channel_suffix))]
    return get_player_by_name(name, manager, server_id)


def get_player_by_name(name: str, manager: Manager, server_id: int) -> Player | None:
    for player in manager.get_board(server_id).players:
        if player.name.lower() == name.strip().lower():
            return player
    return None

def get_orders_log(guild: Guild) -> GuildChannel | None:
    for channel in guild.channels:
        # FIXME move "orders" and "gm channels" to bot.config
        if (channel.name.lower() == "orders-log"
                and channel.category is not None
                and channel.category.name.lower() == "gm channels"
        ):
            return channel
    return None

def is_player_channel(player_role: str, channel: commands.Context.channel) -> bool:
    player_channel = player_role.lower() + config.player_channel_suffix
    return player_channel == channel.name and config.is_player_category(channel.category.name)


def get_keywords(command: str) -> list[str]:
    """Command is split by whitespace with '_' representing whitespace in a concept to be stuck in one word.
    e.g. 'A New_York - Boston' becomes ['A', 'New York', '-', 'Boston']"""
    keywords = command.split(" ")
    for i in range(len(keywords)):
        for j in range(len(keywords[i])):
            if keywords[i][j] in whitespace_dict:
                keywords[i] = keywords[i][:j] + " " + keywords[i][j + 1 :]

    for i in range(len(keywords)):
        keywords[i] = _manage_coast_signature(keywords[i])

    return keywords


def _manage_coast_signature(keyword: str) -> str:
    for coast_key, coast_val in coast_dict.items():
        # we want to make sure this was a separate word like "zapotec ec" and not part of a word like "zapotec"
        suffix = f" {coast_val}"
        if keyword.endswith(suffix):
            # remove the suffix
            keyword = keyword[: len(keyword) - len(suffix)]
            # replace the suffix with the one we expect
            new_suffix = f" {coast_key}"
            keyword += f" {new_suffix}"
    return keyword


def get_unit_type(command: str) -> UnitType | None:
    command = command.strip()
    if command in unit_dict[_army]:
        return UnitType.ARMY
    if command in unit_dict[_fleet]:
        return UnitType.FLEET
    return None

def log_command(
        remote_logger: logging.Logger,
        ctx: discord.ext.commands.Context,
        message: str,
        *,
        level=logging.INFO
) -> None:
    # FIXME Should probably delete this function and use a logging formatter instead
    _log_command(
        remote_logger,
        ctx.message.content,
        ctx.guild.name,
        ctx.channel.name,
        ctx.author.name,
        message,
        level=level
    )

def _log_command(
        remote_logger: logging.Logger,
        invoke_message: str,
        guild: str,
        channel: str,
        invoker: str,
        message: str,
        *,
        level=logging.INFO
) -> None:
    # FIXME Should probably delete this function and use a logging formatter instead

    if level <= logging.DEBUG:
        command_len_limit = -1
    else:
        command_len_limit = 40

    # this might be too expensive?
    command = invoke_message[:command_len_limit].encode('unicode_escape').decode('utf-8')
    if len(invoke_message) > 40:
        command += "..."

    # temporary handling for bad error messages should be removed when we are nolonger passing
    # messages intended for Discord to this function. FIXME
    message = message.encode('unicode_escape').decode('utf-8')

    remote_logger.log(
        level,
        f"[{guild}][#{channel}]({invoker}) - "
        f"'{command}' -> "
        f"{message}"
    )

async def send_message_and_file(
        *,
        channel: commands.Context.channel,
        title: str = None,
        message: str = None,
        messages: [str] = None,
        embed_colour: str = None,
        file: str = None,
        file_name: str = None,
        file_in_embed: bool = None,
        footer_content: str = None,
        footer_datetime: datetime.datetime = None,
        fields: List[Tuple[str, str]] = None,
        convert_svg: bool = False,
        **_
) -> Message:

    if not embed_colour:
        embed_colour = "#fc71c4"

    if convert_svg and file and file_name:
        file, file_name = await svg_to_png(file, file_name)

    if fields:
        for i, field in enumerate(fields):
            if len(field[0]) > 256 or len(field[1]) > 1024:
                title, body = fields.pop(i)
                if not message:
                    message = ""
                message += (f"\n" 
                            f"### {title}\n" if title.strip() else f"{title}\n" 
                            f"{body}")

    if message and messages:
        messages = [message] + messages
    elif message:
        messages = [message]

    embeds = []
    if messages:
        while messages:
            message = messages.pop()
            while message:
                cutoff = discord_embed_description_limit
                # Try to find an even line break to split the long messages on
                if len(message) > discord_embed_description_limit:
                    cutoff = message.rfind("\n", 0, discord_embed_description_limit)
                    # otherwise split at limit
                    if cutoff == -1:
                        cutoff = message.rfind(" ", 0, discord_embed_description_limit)
                        if cutoff == -1:
                            cutoff = discord_embed_description_limit
                embed = Embed(
                    title=title,
                    description=message[:cutoff],
                    colour=Colour.from_str(embed_colour),
                )
                # ensure only first embed has title
                title = None

                # check that embed totals aren't over the total message embed character limit.
                if sum(map(len, embeds)) + len(embed) > discord_embed_total_limit or len(embeds) == 10:
                    await channel.send(embeds=embeds)
                    embeds = []

                embeds.append(embed)

                message = message[cutoff:].strip()

    if not embeds:
        embeds = [Embed(
            title=title,
            colour=Colour.from_str(embed_colour)
        )]
        title = ""

    if fields:
        for field in fields:
            if (len(embeds[-1].fields) == 25
                    or sum(map(len, embeds)) + sum(map(len, field)) > discord_embed_total_limit
                    or len(embeds) == 10):
                await channel.send(embeds=embeds)
                embeds = [Embed(
                    title=title,
                    colour=Colour.from_str(embed_colour)
                )]
                title = ""

            embeds[-1].add_field(name=field[0], value=field[1], inline=True)

    discord_file = None
    if file is not None:
        if file_name[-4:].lower() == ".png" and len(file) > discord_file_limit:
            _log_command(
                logger,
                "?",
                channel.guild.name,
                channel.name,
                "?",
                f"png is too big ({len(file)}); converting to jpg"
            )
            file, file_name = await png_to_jpg(file, file_name)
            if len(file) > discord_file_limit:
                _log_command(
                    logger,
                    "?",
                    channel.guild.name,
                    channel.name,
                    "?",
                    f"jpg is too big ({len(file)})"
                )
                if is_gm_channel(channel):
                    message = "Try `.vm true` to get an svg"
                else:
                    message = "Please contact your GM"
                await send_message_and_file(
                    channel=channel,
                    title="File too larger",
                    message=message
                )
                file = None
                file_name = None
                discord_file = None

    if file is not None:
        with io.BytesIO(file) as vfile:
            discord_file = discord.File(fp=vfile, filename=file_name)

        if file_in_embed or (file_in_embed is None and any(map(lambda x: file_name.lower().endswith(x), (
                        ".png", ".jpg", ".jpeg"#, ".gif", ".gifv", ".webm", ".mp4", "wav", ".mp3", ".ogg"
        )))):
            embeds[-1].set_image(url=f"attachment://{discord_file.filename.replace(' ', '_')}")

    if footer_datetime or footer_content:
        embeds[-1].set_footer(
            text=footer_content,
            icon_url="https://cdn.discordapp.com/icons/1201167737163104376/f78e67edebfdefad8f3ee057ad658acd.webp"
                     "?size=96&quality=lossless"
        )

        embeds[-1].timestamp = footer_datetime

    return await channel.send(embeds=embeds, file=discord_file)


def get_orders(board: Board, player_restriction: Player | None, ctx: Context, fields: bool = False) -> str | List[Tuple[str, str]]:
    if fields:
        response = []
    else:
        response = ""
    if phase.is_builds(board.phase):
        for player in sorted(board.players, key=lambda sort_player: sort_player.name):
            if not player_restriction or player == player_restriction:

                if (player_role := get_role_by_player(player, ctx.guild.roles)) is not None:
                    player_name = player_role.mention
                else:
                    player_name = player.name

                title = f"**{player_name}**: ({len(player.centers)}) ({'+' if len(player.centers) - len(player.units) >= 0 else ''}{len(player.centers) - len(player.units)})"
                body = ""
                for unit in player.build_orders:
                    body += f"\n{unit}"

                if fields:
                    response.append((f"", f"{title}{body}"))
                else:
                    response += f"\n{title}{body}"
        return response
    else:

        if player_restriction is None:
            players = board.players
        else:
            players = {player_restriction}

        for player in sorted(players, key=lambda p: p.name):
            if phase.is_retreats(board.phase):
                in_moves = lambda u: u == u.province.dislodged_unit
            else:
                in_moves = lambda _: True
            moving_units = [unit for unit in player.units if in_moves(unit)]
            ordered = [unit for unit in moving_units if unit.order is not None]
            missing = [unit for unit in moving_units if unit.order is None]

            if (player_role := get_role_by_player(player, ctx.guild.roles)) is not None:
                player_name = player_role.mention
            else:
                player_name = player.name

            title = f"**{player_name}** ({len(ordered)}/{len(moving_units)})"
            body = ""
            if missing:
                body += f"__Missing Orders:__\n"
                for unit in sorted(missing, key=lambda _unit: _unit.province.name):
                    body += f"{unit}\n"
            if ordered:
                body += f"__Submitted Orders:__\n"
                for unit in sorted(ordered, key=lambda _unit: _unit.province.name):
                    body += f"{unit} {unit.order}\n"

            if fields:
                response.append((f"", f"{title}\n{body}"))
            else:
                response += f"{title}\n{body}"

        return response


def get_filtered_orders(board: Board, player_restriction: Player) -> str:
    visible = board.get_visible_provinces(player_restriction)
    if phase.is_builds(board.phase):
        response = ""
        for player in sorted(board.players, key=lambda sort_player: sort_player.name):
            if not player_restriction or player == player_restriction:
                visible = [order for order in player.build_orders if order.location.as_province() in visible]

                if len(visible) > 0:
                    response += f"\n**{player.name}**: ({len(player.centers)}) ({'+' if len(player.centers) - len(player.units) >= 0 else ''}{len(player.centers) - len(player.units)})"
                    for unit in visible:
                        response += f"\n{unit}"
        return response
    else:
        response = ""

        for player in board.players:
            if phase.is_retreats(board.phase):
                in_moves = lambda u: u == u.province.dislodged_unit
            else:
                in_moves = lambda _: True
            moving_units = [unit for unit in player.units if in_moves(unit) and unit.province in visible]

            if len(moving_units) > 0:
                ordered = [unit for unit in moving_units if unit.order is not None]
                missing = [unit for unit in moving_units if unit.order is None]

                response += f"**{player.name}** ({len(ordered)}/{len(moving_units)})\n"
                if missing:
                    response += f"__Missing Orders:__\n"
                    for unit in sorted(missing, key=lambda _unit: _unit.province.name):
                        response += f"{unit}\n"
                if ordered:
                    response += f"__Submitted Orders:__\n"
                    for unit in sorted(ordered, key=lambda _unit: _unit.province.name):
                        response += f"{unit} {unit.order}\n"

        return response
