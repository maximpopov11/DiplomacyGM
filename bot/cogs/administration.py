import logging
import os
import re

from discord import HTTPException, NotFound, TextChannel
from discord.ext import commands
from discord.utils import find as discord_find

from bot import config
from bot import perms
from bot.utils import log_command, parse_season, send_message_and_file, upload_map_to_archive
from diplomacy.persistence.db.database import get_connection
from diplomacy.persistence.manager import Manager

logger = logging.getLogger(__name__)
manager = Manager()


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @perms.superuser_only("send a GM announcement")
    async def announce(self, ctx: commands.Context) -> None:
        guilds_with_games = manager.list_servers()
        content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        content = re.sub(r"<@&[0-9]{16,20}>", r"{}", content)
        roles = list(map(lambda role: role.name, ctx.message.role_mentions))
        message = ""
        for server in ctx.bot.guilds:
            if server is None:
                continue
            admin_chat_channel = next(
                channel for channel in server.channels if config.is_gm_channel(channel)
            )
            if admin_chat_channel is None:
                message += f"\n- ~~{server.name}~~ Couldn't find admin channel"
                continue

            message += f"\n- {server.name}"
            if server.id in guilds_with_games:
                board = manager.get_board(server.id)
                message += f" - {board.phase.name} {board.get_year_str()}"
            else:
                message += f" - no active game"

            server_roles = []
            for role_name in roles:
                for role in server.roles:
                    if role.name == role_name:
                        server_roles.append(role.mention)
                        break
                else:
                    server_roles.append(role_name)

            if len(server_roles) > 0:
                await admin_chat_channel.send(
                    ("||" + "{}" * len(server_roles) + "||").format(*server_roles)
                )
            await send_message_and_file(
                channel=admin_chat_channel,
                title="DiploGM Announcement",
                message=content.format(*server_roles),
            )
        log_command(
            logger, ctx, f"Sent Announcement into {len(ctx.bot.guilds)} servers"
        )
        await send_message_and_file(
            channel=ctx.channel,
            title=f"Announcement sent to {len(ctx.bot.guilds)} servers:",
            message=message,
        )

    @commands.command(hidden=True)
    @perms.superuser_only("list servers")
    async def servers(self, ctx: commands.Context) -> None:
        servers_with_games = manager.list_servers()
        message = ""
        args = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with).split(
            " "
        )
        send_id = "id" in args
        send_invite = "invite" in args
        for server in ctx.bot.guilds:
            if server is None:
                continue

            channels = server.channels
            for channel in channels:
                if isinstance(channel, TextChannel):
                    break
            else:
                message += f"\n- {server.name} - Could not find a channel for invite"
                continue

            if server.id in servers_with_games:
                servers_with_games.remove(server.id)
                board = manager.get_board(server.id)
                board_state = f" - {board.phase.name} {board.get_year_str()}"
            else:
                board_state = f" - no active game"

            if send_invite:
                try:
                    invite = await channel.create_invite(max_age=300)
                except (HTTPException, NotFound):
                    message += f"\n- {server.name} - Could not create invite"
                else:
                    message += f"\n- [{server.name}](<{invite.url}>)"
            else:
                message += f"\n- {server.name}"

            message += board_state
            if send_id:
                message += f" - {server.id}"

        # Servers with games the bot is not in
        if servers_with_games:
            message += f"\n There is a further {len(servers_with_games)} games in servers I am no longer in"

        log_command(logger, ctx, f"Found {len(ctx.bot.guilds)} servers")
        await send_message_and_file(
            channel=ctx.channel, title=f"{len(ctx.bot.guilds)} Servers", message=message
        )

    @commands.command(hidden=True)
    @perms.superuser_only("leave server")
    async def leave_server(self, ctx: commands.Context) -> None:
        leave_id = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
        try:
            leave_id = int(leave_id)
        except ValueError:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Failed to parse server ID",
                embed_colour=config.ERROR_COLOUR,
            )
            return

        for server in ctx.bot.guilds:
            if server.id == leave_id:
                name = server.name
                # icon = server.icon.url
                try:
                    await server.leave()
                except HTTPException:
                    await send_message_and_file(
                        channel=ctx.channel,
                        title=f"Failed to leave: {name}",
                        embed_colour=config.ERROR_COLOUR,
                    )
                else:
                    await send_message_and_file(
                        channel=ctx.channel, title=f"Left Server {name}"
                    )
                return
        else:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"Failed to find server",
                embed_colour=config.ERROR_COLOUR,
            )

    @commands.command(hidden=True)
    @perms.superuser_only("allocate roles to user(s)")
    async def bulk_allocate_role(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        if guild is None:
            return

        # extract roles to be allocated based off of mentions
        # .bulk_allocate_role <@B1.4 Player> <@B1.4 GM Team> ...
        roles = ctx.message.role_mentions
        role_names = list(map(lambda r: r.name, roles))

        for role in roles.copy():
            name = role.name.lower()
            if config.is_gm_role(name) or config.is_mod_role(name):
                await send_message_and_file(
                    channel=ctx.channel,
                    title="Error!",
                    embed_color=config.ERROR_COLOUR,
                    message=f"Not allowed to allocate this role using DiploGM: {role.mention}",
                )
                roles.remove(role)

        if len(roles) == 0:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="No roles were supplied to allocate. Please include a role mention in the command.",
            )
            return

        # parse usernames from trailing contents
        # .bulk_allocate_role <@B1.4 Player> elisha thisisflare kingofprussia ...
        content = ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)

        usernames = []
        components = content.split(" ")
        for comp in components:
            if comp == "":
                continue

            match = re.match(r"<@&\d+>", comp)
            if match:
                continue

            usernames.append(comp)

        success_count = 0
        failed = []
        skipped = []
        for user in usernames:
            # FIND USER FROM USERNAME
            member = discord_find(
                lambda m: m.name == user,
                guild.members,
            )

            if not member or member is None:
                failed.append((user, "Member not Found"))
                continue

            for role in roles:
                if role in member.roles:
                    skipped.append((user, f"already had role @{role.name}"))
                    continue

                try:
                    await member.add_roles(role)
                    success_count += 1
                except Exception as e:
                    failed.append((user, f"Error Adding Role- {e}"))

        failed_out = "\n".join([f"{u}: {m}" for u, m in failed])
        skipped_out = "\n".join([f"{u}: {m}" for u, m in skipped])
        out = (
            f"Allocated Roles {', '.join(role_names)} to {len(usernames)} users.\n"
            + f"Succeeded in applying a role {success_count} times.\n"
            + f"Failed {len(failed)} times.\n"
            + f"Skipped {len(skipped)} times for already having the role.\n"
            + "----\n"
        )

        if len(failed_out) > 0:
            out += "----\n"
            out += f"Failed Reasons:\n{failed_out}\n"

        if len(skipped_out) > 0:
            out += "----\n"
            out += f"Skipped Reasons\n{skipped_out}\n"

        await send_message_and_file(
            channel=ctx.channel, title="Wave Allocation Info", message=out
        )
    
    @commands.command(hidden=True)
    @perms.superuser_only("Uploads map to archive")
    async def archive_upload(self, ctx: commands.Context) -> None:
        if "maps_sas_token" not in os.environ:
            await send_message_and_file(
                channel=ctx.channel,
                title=f"maps_sas_token is not defined in environment variables",
                embed_colour=config.ERROR_COLOUR,
            )
            return
        arguments = (
            ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
            .strip()
            .lower()
            .split()
        )
        server_id = int(arguments[0])
        board = manager.get_board(server_id)
        season = parse_season(arguments[1:], board.get_year_str())
        file, _ = manager.draw_map(
            ctx.guild.id,
            draw_moves=True,
            turn=season,
        )
        await upload_map_to_archive(ctx, server_id, board, file, season)

    @commands.command(
        brief="Execute Arbitrary Python",
        description="Execute a python snippet on the current board state.\nWARNING: Changes made to the board state are saved to the database.",
        help="""Example:
        ```python
        for player in board.players:
            print(player.name)
        ```
    """,
    )
    @perms.superuser_only("Execute arbitrary python code")
    async def exec_py(self, ctx: commands.Context) -> None:
        class ContainedPrinter:
            def __init__(self):
                self.text = ""

            def __call__(self, *args):
                self.text += " ".join(map(str, args)) + "\n"

        board = manager.get_board(ctx.guild.id)
        code = (
            ctx.message.content.removeprefix(ctx.prefix + ctx.invoked_with)
            .strip()
            .strip("`")
        )

        embed_print = ContainedPrinter()

        try:
            exec(code, {"print": embed_print, "board": board})
        except Exception as e:
            embed_print("\n" + repr(e))

        if embed_print.text:
            await send_message_and_file(channel=ctx.channel, message=embed_print.text)
        manager._database.delete_board(board)

        manager._database.save_board(ctx.guild.id, board)

    # @commands.command(
    #     brief="Execute Arbitrary SQL",
    #     description="Perform an SQL query on the production database.\n\nONLY TO BE USED IN THE MOST EXTREME CASES\nONLY USE IF YOU ARE ABSOLUTELY SURE OF WHAT YOU ARE DOING.",
    #     help="""Example:
    # `.exec_sql "DELETE FROM units WHERE board_id=? AND phase=? AND owner=?" <server_id> "0 Fall Moves" England`
    # `.exec_sql "UPDATE provinces SET owner=? WHERE board_id=? AND phase=?" Aymara <server_id> "2 Spring Moves"`
    # """,
    # )
    # @perms.superuser_only("Execute arbitrary SQL code")
    # async def exec_sql(self, ctx: commands.Context, query: str, *args) -> None:
    #     conn = get_connection()
    #     conn.execute_arbitrary_sql(query, args)


async def setup(bot):
    cog = AdminCog(bot)
    await bot.add_cog(cog)
