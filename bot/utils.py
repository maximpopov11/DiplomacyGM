import asyncio
import datetime
import io
import os
import re
import logging
from subprocess import PIPE
from typing import List, Tuple


import discord
from discord import Embed, Colour, Guild, Message, Thread
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands import Context

from bot import config
from diplomacy.adjudicator.utils import svg_to_png, png_to_jpg
from diplomacy.persistence import phase
from diplomacy.persistence.board import Board
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.phase import Phase
from diplomacy.persistence.player import Player
from diplomacy.persistence.unit import UnitType

logger = logging.getLogger(__name__)

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


def is_superuser(author: commands.Context.author) -> bool:
    return author.id in [
        1217203346511761428,  # eebop
        332252245259190274,  # Icecream Guy
        169995316680982528,  # Bumble
        450636420558618625,  # Flare
        490633966974533640,  # Elle
        200279271380353025,  # KingOfPrussia
        1352388421003251833,  # Chloe
        285108244714881024,  # aahoughton (elle-approved)
        134870832651567104, # Golden Kumquat (elle-approved)
    ]


def is_moderator(author: commands.Context.author) -> bool:
    for role in author.roles:
        if config.is_mod_role(role.name):
            return True

    return False


def is_gm(author: commands.Context.author) -> bool:
    for role in author.roles:
        if config.is_gm_role(role.name):
            return True
    return False


def is_gm_channel(channel: commands.Context.channel) -> bool:
    return config.is_gm_channel(channel.name) and config.is_gm_category(
        channel.category.name
    )


def get_player_by_role(
    author: commands.Context.author, manager: Manager, server_id: int
) -> Player | None:
    for role in author.roles:
        for player in manager.get_board(server_id).players:
            if simple_player_name(player.name) == simple_player_name(role.name):
                return player
    return None


def get_role_by_player(player: Player, roles: Guild.roles) -> discord.Role | None:
    for role in roles:
        if simple_player_name(role.name) == simple_player_name(player.name):
            return role
    return None


def get_player_by_channel(
    channel: commands.Context.channel,
    manager: Manager,
    server_id: int,
    ignore_category=False,
) -> Player | None:
    # thread -> main channel
    if isinstance(channel, Thread):
        channel = channel.parent

    board = manager.get_board(server_id)
    name = channel.name
    if (not ignore_category) and not config.is_player_category(channel.category.name):
        return None

    if board.is_chaos() and name.endswith("-void"):
        name = name[:-5]
    else:
        if not name.endswith(config.player_channel_suffix):
            return None

        name = name[: -(len(config.player_channel_suffix))]

    try:
        return board.get_cleaned_player(name)
    except ValueError:
        pass
    try:
        return board.get_cleaned_player(simple_player_name(name))
    except ValueError:
        return None

    return None


# FIXME this is done pretty poorly
async def get_channel_by_player(
    player: Player, ctx: commands.Context, manager: Manager
) -> GuildChannel:
    guild = ctx.guild
    guild_id = guild.id
    board = manager.get_board(guild_id)

    channel_name = simple_player_name(player.name) + config.player_channel_suffix

    for category in guild.categories:
        if not config.is_player_category(category.name) and not board.is_chaos():
            continue

        for channel in category.channels:
            if channel.name == channel_name:
                return channel

    return None


# I'm sorry this is a bad function name. I couldn't think of anything better and I'm in a rush
def simple_player_name(name: str):
    return name.lower().replace("-", " ").replace("'", "").replace(".", "")


def get_player_by_name(name: str, manager: Manager, server_id: int) -> Player | None:
    for player in manager.get_board(server_id).players:
        if simple_player_name(player.name) == simple_player_name(name):
            return player
    return None


def get_maps_channel(guild: Guild) -> GuildChannel | None:
    for channel in guild.channels:
        if (
            channel.name.lower() == "maps"
            and channel.category is not None
            and channel.category.name.lower() == "gm channels"
        ):
            return channel
    return None


def get_orders_log(guild: Guild) -> GuildChannel | None:
    for channel in guild.channels:
        # FIXME move "orders" and "gm channels" to bot.config
        if (
            channel.name.lower() == "orders-log"
            and channel.category is not None
            and channel.category.name.lower() == "gm channels"
        ):
            return channel
    return None


def is_player_channel(player_role: str, channel: commands.Context.channel) -> bool:
    player_channel = player_role + config.player_channel_suffix
    return simple_player_name(player_channel) == simple_player_name(
        channel.name
    ) and config.is_player_category(channel.category.name)


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
    level=logging.INFO,
) -> None:
    # FIXME Should probably delete this function and use a logging formatter instead
    log_command_no_ctx(
        remote_logger,
        ctx.message.content,
        ctx.guild.name,
        ctx.channel.name,
        ctx.author.name,
        message,
        level=level,
    )


def log_command_no_ctx(
    remote_logger: logging.Logger,
    invoke_message: str,
    guild: str,
    channel: str,
    invoker: str,
    message: str,
    *,
    level=logging.INFO,
) -> None:
    # FIXME Should probably delete this function and use a logging formatter instead

    if level <= logging.DEBUG:
        command_len_limit = -1
    else:
        command_len_limit = 40

    # this might be too expensive?
    command = (
        invoke_message[:command_len_limit].encode("unicode_escape").decode("utf-8")
    )
    if len(invoke_message) > 40:
        command += "..."

    # temporary handling for bad error messages should be removed when we are nolonger passing
    # messages intended for Discord to this function. FIXME
    message = message.encode("unicode_escape").decode("utf-8")

    remote_logger.log(
        level, f"[{guild}][#{channel}]({invoker}) - " f"'{command}' -> " f"{message}"
    )


async def send_message_and_file(
    *,
    channel: commands.Context.channel,
    title: str | None = None,
    message: str | None = None,
    messages: list[str] | None = None,
    embed_colour: str | None = None,
    file: str | None = None,
    file_name: str | None = None,
    file_in_embed: bool | None = None,
    footer_content: str | None = None,
    footer_datetime: datetime.datetime | None = None,
    fields: List[Tuple[str, str]] | None = None,
    convert_svg: bool = False,
    **_,
) -> Message:

    if not embed_colour:
        embed_colour = config.EMBED_STANDARD_COLOUR

    if convert_svg and file and file_name:
        file, file_name = await svg_to_png(file, file_name)

    # Checks embed title and bodies are within limits.
    if fields:
        for i, field in reversed(list(enumerate(fields))):
            if len(field[0]) > 256 or len(field[1]) > 1024:
                field_title, field_body = fields.pop(i)
                if not message:
                    message = ""
                message += (
                    f"\n" f"### {field_title}\n"
                    if field_title.strip()
                    else f"{field_title}\n" f"{field_body}"
                )

    if message and messages:
        messages = [message] + messages
    elif message:
        messages = [message]

    embeds = []
    if messages:
        while messages:
            message = messages.pop()
            while message:
                cutoff = -1
                if len(message) <= discord_embed_description_limit:
                    cutoff = len(message)
                # Try to find an even line break to split the long messages on
                if cutoff == -1:
                    cutoff = message.rfind("\n", 0, discord_embed_description_limit)
                if cutoff == -1:
                    cutoff = message.rfind(" ", 0, discord_embed_description_limit)
                # otherwise split at limit
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
                if (
                    sum(map(len, embeds)) + len(embed) > discord_embed_total_limit
                    or len(embeds) == 10
                ):
                    await channel.send(embeds=embeds)
                    embeds = []

                embeds.append(embed)

                message = message[cutoff:].strip()

    if not embeds:
        embeds = [Embed(title=title, colour=Colour.from_str(embed_colour))]
        title = ""

    if fields:
        for field in fields:
            if (
                len(embeds[-1].fields) == 25
                or sum(map(len, embeds)) + sum(map(len, field))
                > discord_embed_total_limit
                or len(embeds) == 10
            ):
                await channel.send(embeds=embeds)
                embeds = [
                    Embed(
                        title=title,
                        colour=Colour.from_str(embed_colour),
                    )
                ]
                title = ""

            embeds[-1].add_field(name=field[0], value=field[1], inline=True)

    discord_file = None
    if file is not None:
        if file_name[-4:].lower() == ".png" and len(file) > discord_file_limit:
            log_command_no_ctx(
                logger,
                "?",
                channel.guild.name,
                channel.name,
                "?",
                f"png is too big ({len(file)}); converting to jpg",
            )
            file, file_name, error = await png_to_jpg(file, file_name)
            error = re.sub("\\s+", " ", str(error)[2:-1])
            if len(error) > 0:
                log_command_no_ctx(
                    logger,
                    "?",
                    channel.guild.name,
                    channel.name,
                    "?",
                    f"png to jpeg conversion errors: {error}",
                )
            if len(file) > discord_file_limit or len(file) == 0:
                log_command_no_ctx(
                    logger,
                    "?",
                    channel.guild.name,
                    channel.name,
                    "?",
                    f"jpg is too big ({len(file)})",
                )
                if is_gm_channel(channel):
                    message = "Try `.vm true` to get an svg"
                else:
                    message = "Please contact your GM"
                await send_message_and_file(
                    channel=channel, title="File too large", message=message
                )
                file = None
                file_name = None
                discord_file = None

    if file is not None:
        with io.BytesIO(file) as vfile:
            discord_file = discord.File(fp=vfile, filename=file_name)

        if file_in_embed or (
            file_in_embed is None
            and any(
                map(
                    lambda x: file_name.lower().endswith(x),
                    (
                        ".png",
                        ".jpg",
                        ".jpeg",  # , ".gif", ".gifv", ".webm", ".mp4", "wav", ".mp3", ".ogg"
                    ),
                )
            )
        ):
            embeds[-1].set_image(
                url=f"attachment://{discord_file.filename.replace(' ', '_')}"
            )

    if footer_datetime or footer_content:
        embeds[-1].set_footer(
            text=footer_content,
            icon_url="https://cdn.discordapp.com/icons/1201167737163104376/f78e67edebfdefad8f3ee057ad658acd.webp"
            "?size=96&quality=lossless",
        )

        embeds[-1].timestamp = footer_datetime

    return await channel.send(embeds=embeds, file=discord_file)


def get_orders(
    board: Board,
    player_restriction: Player | None,
    ctx: Context,
    fields: bool = False,
    subset: str | None = None,
    blind: bool = False,
) -> str | List[Tuple[str, str]]:
    if fields:
        response = []
    else:
        response = ""
    if phase.is_builds(board.phase):
        for player in sorted(board.players, key=lambda sort_player: sort_player.name):
            if not player_restriction and (
                len(player.centers) + len(player.units) == 0
            ):
                continue

            if not player_restriction or player == player_restriction:

                if (
                    player_role := get_role_by_player(player, ctx.guild.roles)
                ) is not None:
                    player_name = player_role.mention
                else:
                    player_name = player.name

                if subset == "missing" and abs(
                    len(player.centers) - len(player.units) - player.waived_orders
                ) == len(player.build_orders):
                    continue
                if (
                    subset == "submitted"
                    and len(player.build_orders) == 0
                    and player.waived_orders == 0
                ):
                    continue

                title = f"**{player_name}**: ({len(player.centers)}) ({'+' if len(player.centers) - len(player.units) >= 0 else ''}{len(player.centers) - len(player.units)})"
                body = ""
                if blind:
                    body = f" ({len(player.build_orders) + player.waived_orders})"
                else:
                    for unit in player.build_orders | set(
                        player.vassal_orders.values()
                    ):
                        body += f"\n{unit}"
                    if player.waived_orders > 0:
                        body += f"\nWaive {player.waived_orders}"

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
            if not player_restriction and (
                len(player.centers) + len(player.units) == 0
            ):
                continue

            if phase.is_retreats(board.phase):
                in_moves = lambda u: u == u.province.dislodged_unit
            else:
                in_moves = lambda _: True
            moving_units = [unit for unit in player.units if in_moves(unit)]
            ordered = [unit for unit in moving_units if unit.order is not None]
            missing = [unit for unit in moving_units if unit.order is None]

            if subset == "missing" and not missing:
                continue
            if subset == "submitted" and not ordered:
                continue

            if (player_role := get_role_by_player(player, ctx.guild.roles)) is not None:
                player_name = player_role.mention
            else:
                player_name = player.name

            title = f"**{player_name}** ({len(ordered)}/{len(moving_units)})"
            body = ""
            if blind:
                body = ""
            else:
                if missing and subset != "submitted":
                    body += f"__Missing Orders:__\n"
                    for unit in sorted(missing, key=lambda _unit: _unit.province.name):
                        body += f"{unit}\n"
                if ordered and subset != "missing":
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
                visible = [
                    order
                    for order in player.build_orders
                    if order.location.as_province() in visible
                ]

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
            moving_units = [
                unit
                for unit in player.units
                if in_moves(unit) and unit.province in visible
            ]

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


def fish_pop_model(Fish, t, growth_rate, carrying_capacity):
    dFishdt = growth_rate * Fish * (1 - Fish / carrying_capacity)
    return dFishdt


def parse_season(
    arguments: list[str], default_year: str
) -> tuple[str, phase.Phase] | None:
    year, season, retreat = default_year, None, False
    for s in arguments:
        if s.isnumeric() and int(s) > 1640:
            year = s

        if s.lower() in ["spring", "s", "sm", "sr"]:
            season = "Spring"
        elif s.lower() in ["fall", "f", "fm", "fr"]:
            season = "Fall"
        elif s.lower() in ["winter", "w", "wa"]:
            season = "Winter"

        if s.lower() in ["retreat", "retreats", "r", "sr", "fr"]:
            retreat = True

    if season is None:
        return None
    if season == "Winter":
        parsed_phase = phase.get("Winter Builds")
    else:
        parsed_phase = phase.get(season + " " + ("Retreats" if retreat else "Moves"))
    return (year, parsed_phase)

def get_value_from_timestamp(timestamp: str) -> int | None:
    if len(timestamp) == 10 and timestamp.isnumeric():
        return int(timestamp)

    match = re.match(r"<t:(\d{10}):\w>", timestamp)
    if match:
        return int(match.group(1))

    return None

async def upload_map_to_archive(ctx: commands.Context, server_id: int, board: Board, map: str, turn: tuple[str, phase] | None = None) -> None:
    if "maps_sas_token" not in os.environ:
        return
    if turn is None:
        turnstr = f"{(board.year + board.year_offset) % 100}{board.phase.shortname}"
    else:
        turnstr = f"{int(turn[0]) % 100}{turn[1].shortname}"
    url = None
    with open("gamelist.tsv", "r") as gamefile:
        for server in gamefile:
            server_info = server.strip().split("\t")
            if str(server_id) == server_info[0]:
                url = f"{os.environ['maps_url']}/{server_info[1]}/{server_info[2]}/{turnstr}m.png{os.environ['maps_sas_token']}"
                break
    if url is None:
        return
    png_map, _ = await svg_to_png(map, url)
    p = await asyncio.create_subprocess_shell(
        f'azcopy copy "{url}" --from-to PipeBlob --content-type image/png',
        stdout=PIPE,
        stdin=PIPE,
        stderr=PIPE,
    )
    data, error = await p.communicate(input=png_map)
    error = error.decode()
    await send_message_and_file(
        channel=ctx.channel,
        title=f"Uploaded map to archive",
    )
    log_command(
        logger,
        ctx,
        message=(
            f"Map uploading failed: {error}"
            if len(error) > 0
            else "Uploaded map to archive"
        ),
    )
