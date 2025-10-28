import logging
import re
from typing import Any

from discord.ext import commands

from bot import config
from bot import perms
from bot.parse_order import parse_order, parse_remove_order
from bot.utils import get_orders, log_command, parse_season, send_message_and_file
from diplomacy.persistence.manager import Manager
from diplomacy.persistence.player import Player

logger = logging.getLogger(__name__)
manager = Manager()


class PlayerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        brief="Submits orders; there must be one and only one order per line.",
        description="""Submits orders: 
    There must be one and only one order per line.
    A variety of keywords are supported: e.g. '-', '->', 'move', and 'm' are all supported for a move command.
    Supplying the unit type is fine but not required: e.g. 'A Ghent -> Normandy' and 'Ghent -> Normandy' are the same
    If anything in the command errors, we recommend resubmitting the whole order message.
    *During Build phases only*, you have to specify multi-word provinces with underscores; e.g. Somali Basin would be Somali_Basin (we use a different parser during build phases)
    If you would like to use something that is not currently supported please inform your GM and we can add it.""",
        aliases=["o", "orders"],
    )
    @perms.player("order")
    async def order(
        self,
        ctx: commands.Context,
        player: Player | None,
    ) -> None:
        board = manager.get_board(ctx.guild.id)

        if player and not board.orders_enabled:
            log_command(logger, ctx, f"Orders locked - not processing")
            await send_message_and_file(
                channel=ctx.channel,
                title="Orders locked!",
                message="If you think this is an error, contact a GM.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        message = parse_order(ctx.message.content, player, board)
        if "title" in message:
            log_command(logger, ctx, message=message["title"], level=logging.DEBUG)
        elif "message" in message:
            log_command(
                logger, ctx, message=message["message"][:100], level=logging.DEBUG
            )
        elif "messages" in message and len(message["messages"]) > 0:
            log_command(
                logger, ctx, message=message["messages"][0][:100], level=logging.DEBUG
            )
        await send_message_and_file(channel=ctx.channel, **message)

    @commands.command(
        brief="Removes orders for given units.",
        description="Removes orders for given units (required for removing builds/disbands). "
        "There must be one and only one order per line.",
        aliases=["remove", "rm", "removeorders"],
    )
    @perms.player("remove orders")
    async def remove_order(self, ctx: commands.Context, player: Player | None) -> None:
        board = manager.get_board(ctx.guild.id)

        if player and not board.orders_enabled:
            log_command(logger, ctx, f"Orders locked - not processing")
            await send_message_and_file(
                channel=ctx.channel,
                title="Orders locked!",
                message="If you think this is an error, contact a GM.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)

        message = parse_remove_order(content, player, board)
        log_command(logger, ctx, message=message["message"])
        await send_message_and_file(channel=ctx.channel, **message)

    @commands.command(
        brief="Outputs your current submitted orders.",
        description="Outputs your current submitted orders. "
        "Use .view_map to view a sample moves map of your orders. "
        "Use the 'missing' or 'submitted' argument to view only units without orders or only submitted orders. "
        "Use the 'blind' argument to view only the number of orders submitted.",
        aliases=["v", "view", "vieworders", "view-orders"],
    )
    @perms.player("view orders")
    async def view_orders(self, ctx: commands.Context, player: Player | None) -> None:
        arguments = (
            ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
            .strip()
            .lower()
            .split()
        )
        subset = "missing" if {"missing", "miss", "m"} & set(arguments) else None
        subset = (
            "submitted"
            if {"submitted", "submit", "sub", "s"} & set(arguments)
            else subset
        )

        try:
            board = manager.get_board(ctx.guild.id)

            blind = "blind" in arguments
            order_text = get_orders(board, player, ctx, subset=subset, blind=blind)

        except RuntimeError as err:
            logger.error(err, exc_info=True)
            log_command(
                logger,
                ctx,
                message=f"Failed for an unknown reason",
                level=logging.ERROR,
            )
            await send_message_and_file(
                channel=ctx.channel,
                title="Unknown Error: Please contact your local bot dev",
                embed_colour=config.ERROR_COLOUR,
            )
            return
        log_command(
            logger,
            ctx,
            message=f"Success - generated orders for {board.phase.name} {board.get_year_str()}",
        )
        await send_message_and_file(
            channel=ctx.channel,
            title=f"{board.phase.name} {board.get_year_str()}",
            message=order_text,
        )

    @commands.command(
        brief="Outputs the current map with submitted orders.",
        description="""
        For GMs, all submitted orders are displayed. For a player, only their own orders are displayed.
        GMs may append true as an argument to this to instead get the svg.
        * view_map {arguments}
        Arguments: 
        * pass true|t|svg|s to return an svg
        * pass standard, dark, blue, or pink for different color modes if present
        * pass season and optionally year for older maps
        """,
        aliases=["viewmap", "vm"],
    )
    @perms.player("view map")
    async def view_map(self, ctx: commands.Context, player: Player | None):
        arguments = (
            ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
            .strip()
            .lower()
            .split()
        )
        convert_svg = (player is not None) or not (
            {"true", "t", "svg", "s"} & set(arguments)
        )
        color_arguments = list(config.color_options & set(arguments))
        color_mode = color_arguments[0] if color_arguments else None
        movement_only = "movement" in arguments
        board = manager.get_board(ctx.guild.id)
        season = parse_season(arguments, board.get_year_str())

        year = board.get_year_str() if season is None else season[0]
        phase_str = board.phase.name if season is None else season[1].name

        if player and not board.orders_enabled:
            log_command(logger, ctx, f"Orders locked - not processing")
            await send_message_and_file(
                channel=ctx.channel,
                title="Orders locked!",
                message="If you think this is an error, contact a GM.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        try:
            if not board.fow:
                file, file_name = manager.draw_map(
                    ctx.guild.id,
                    draw_moves=True,
                    player_restriction=player,
                    color_mode=color_mode,
                    turn=season,
                    movement_only=movement_only,
                )
            else:
                file, file_name = manager.draw_fow_players_moves_map(
                    ctx.guild.id, player, color_mode
                )
        except Exception as err:
            logger.error(err, exc_info=True)
            log_command(
                logger,
                ctx,
                message=f"Failed to generate map for an unknown reason",
                level=logging.ERROR,
            )
            await send_message_and_file(
                channel=ctx.channel,
                title="Unknown Error: Please contact your local bot dev",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        log_command(
            logger,
            ctx,
            message=f"Generated moves map for {phase_str} {year}",
        )
        await send_message_and_file(
            channel=ctx.channel,
            title=f"{phase_str} {year}",
            file=file,
            file_name=file_name,
            convert_svg=convert_svg,
            file_in_embed=False,
        )

    @commands.command(
        brief="Outputs the current map without any orders.",
        description="""
        * view_current {arguments}
        Arguments: 
        * pass true|t|svg|s to return an svg
        * pass standard, dark, blue, or pink for different color modes if present
        """,
        aliases=["viewcurrent", "vc"],
    )
    @perms.player("view current")
    async def view_current(self, ctx: commands.Context, player: Player | None) -> None:
        arguments = (
            ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
            .strip()
            .lower()
            .split()
        )
        convert_svg = not ({"true", "t", "svg", "s"} & set(arguments))
        color_arguments = list(config.color_options & set(arguments))
        color_mode = color_arguments[0] if color_arguments else None
        board = manager.get_board(ctx.guild.id)
        season = parse_season(arguments, board.get_year_str())

        year = board.get_year_str() if season is None else season[0]
        phase_str = board.phase.name if season is None else season[1].name

        if player and not board.orders_enabled:
            log_command(logger, ctx, f"Orders locked - not processing")
            await send_message_and_file(
                channel=ctx.channel,
                title="Orders locked!",
                message="If you think this is an error, contact a GM.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        try:
            if not board.fow:
                file, file_name = manager.draw_map(
                    ctx.guild.id, color_mode=color_mode, turn=season
                )
            else:
                file, file_name = manager.draw_fow_current_map(
                    ctx.guild.id, player, color_mode
                )
        except Exception as err:
            logger.error(err, exc_info=True)
            log_command(
                logger,
                ctx,
                message=f"Failed to generate map for an unknown reason",
                level=logging.ERROR,
            )
            await send_message_and_file(
                channel=ctx.channel,
                title="Unknown Error: Please contact your local bot dev",
                embed_colour=config.ERROR_COLOUR,
            )
            return
        log_command(
            logger,
            ctx,
            message=f"Generated current map for {phase_str} {year}",
        )
        await send_message_and_file(
            channel=ctx.channel,
            title=f"{phase_str} {year}",
            file=file,
            file_name=file_name,
            convert_svg=convert_svg,
            file_in_embed=False,
        )

    @commands.command(
        brief="Outputs a interactive svg that you can issue orders in",
        aliases=["g"],
    )
    @perms.player("view gui")
    async def view_gui(self, ctx: commands.Context, player: Player | None) -> None:
        arguments = (
            ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
            .strip()
            .lower()
            .split()
        )
        color_arguments = list(config.color_options & set(arguments))
        color_mode = color_arguments[0] if color_arguments else None
        board = manager.get_board(ctx.guild.id)

        if player and not board.orders_enabled:
            log_command(logger, ctx, f"Orders locked - not processing")
            await send_message_and_file(
                channel=ctx.channel,
                title="Orders locked!",
                message="If you think this is an error, contact a GM.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        try:
            if not board.fow:
                file, file_name = manager.draw_gui_map(
                    ctx.guild.id, color_mode=color_mode
                )
            else:
                file, file_name = manager.draw_fow_gui_map(
                    ctx.guild.id, player_restriction=player, color_mode=color_mode
                )
        except Exception as err:
            log_command(
                logger,
                ctx,
                message=f"Failed to generate map for an unknown reason",
                level=logging.ERROR,
            )
            await send_message_and_file(
                channel=ctx.channel,
                title="Unknown Error: Please contact your local bot dev",
                embed_colour=config.ERROR_COLOUR,
            )
            raise err
            return
        log_command(
            logger,
            ctx,
            message=f"Generated current map for {board.phase.name} {board.get_year_str()}",
        )
        await send_message_and_file(
            channel=ctx.channel,
            title=f"{board.phase.name} {board.get_year_str()}",
            file=file,
            file_name=file_name,
            convert_svg=False,
            file_in_embed=False,
        )

    @commands.command(brief="outputs the provinces you can see")
    @perms.player("view visible provinces")
    async def visible_provinces(
        self, ctx: commands.Context, player: Player | None
    ) -> None:
        board = manager.get_board(ctx.guild.id)

        if not player or not board.fow:
            log_command(logger, ctx, message=f"No fog of war game")
            await send_message_and_file(
                channel=ctx.channel,
                message="This command only works for players in fog of war games.",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        visible_provinces = board.get_visible_provinces(player)
        log_command(
            logger, ctx, message=f"There are {len(visible_provinces)} visible provinces"
        )
        await send_message_and_file(
            channel=ctx.channel, message=", ".join([x.name for x in visible_provinces])
        )
        return


async def setup(bot):
    cog = PlayerCog(bot)
    await bot.add_cog(cog)
