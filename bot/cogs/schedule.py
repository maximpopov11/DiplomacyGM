from copy import deepcopy
import datetime
import json
import logging

from discord.ext import commands, tasks
from discord import Message, User

from bot.bot import DiploGM
from bot import perms
from bot.config import ERROR_COLOUR
from bot.utils import (
    get_value_from_timestamp,
    log_command,
    send_message_and_file,
    log_command_no_ctx,
)
from diplomacy.persistence.manager import Manager

logger = logging.getLogger(__name__)
manager = Manager()

LOOP_FREQUENCY_SECONDS = 30
SAVE_FREQUENCY_SECONDS = 300
MAX_DELAY = datetime.timedelta(minutes=5)
IMPOSSIBLE_COMMANDS = ["schedule", "create_game", "delete_game"]


class ScheduleCog(commands.Cog):
    bot: DiploGM

    def __init__(self, bot):
        self.bot = bot
        self.scheduled_storage = "bot/assets/schedule.json"
        self.scheduled_tasks = {}

        try:
            logger.info("Reading stored scheduled tasks")
            with open(self.scheduled_storage) as f:
                read_tasks = json.load(f)
                for _, task in read_tasks.items():
                    task["created_at"] = datetime.datetime.fromisoformat(
                        task["created_at"]
                    )
                    task["execute_at"] = datetime.datetime.fromisoformat(
                        task["execute_at"]
                    )

                self.scheduled_tasks = read_tasks
            logger.info(f"Obtained {len(self.scheduled_tasks)} stored scheduled tasks")

        except FileNotFoundError:
            logger.warning(
                "Could not load previous store of scheduled tasks because it does not exist: should be located at 'bot/assets/schedule.json'"
            )
        except Exception as e:
            logger.warning(f"Could not load previous store of scheduled tasks: {e}")
            raise e

        self.process_scheduled_tasks.start()

    async def close(self):
        self.process_scheduled_tasks.cancel()
        self.save_scheduled_tasks.cancel()
        with open(self.scheduled_storage, "w") as f:
            for _, task in self.scheduled_tasks.items():
                task["created_at"] = task["created_at"].isoformat()
                task["execute_at"] = task["execute_at"].isoformat()

            json.dump(self.scheduled_tasks, f)

    @commands.command(
        name="schedule",
        brief="Schedule a time for command execution",
        help="""
    Usage:
    .schedule <timestamp> <command> <args>
    .schedule <timestamp> view_map dark
    .schedule <timestamp> ping_players <timestamp>
        """,
    )
    @perms.gm_only("schedule a command")
    async def schedule(
        self,
        ctx: commands.Context,
        timestamp: str,
        command_name: str,
        *,
        content: str = "",
    ):
        guild = ctx.guild
        channel = ctx.channel
        if not guild or not channel:
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        scheduled_time = get_value_from_timestamp(timestamp)
        if not scheduled_time:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Did not mention a nation.",
                embed_colour=ERROR_COLOUR,
            )
            return

        # check schedule time is in the future
        scheduled_time = datetime.datetime.fromtimestamp(
            scheduled_time, tz=datetime.timezone.utc
        )

        if scheduled_time <= now:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message="Don't schedule a command to occur in the past.",
                embed_colour=ERROR_COLOUR,
            )
            return

        # check command is real and prevent recursive scheduling
        command_name = command_name.removeprefix(self.bot.command_prefix)
        cmd: commands.Command = ctx.bot.get_command(command_name)
        if cmd is None:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message=f"Command '{command_name}' is not understood.",
                embed_colour=ERROR_COLOUR,
            )
            return

        elif command_name in IMPOSSIBLE_COMMANDS:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error",
                message=f"Command '{command_name}' can't be scheduled.",
                embed_colour=ERROR_COLOUR,
            )
            return

        scheduled_task = {
            "invoking_user_id": ctx.author.id,
            "invoking_user_name": ctx.author.name,
            "invoking_msg_id": ctx.message.id,
            "guild_id": guild.id,
            "channel_id": channel.id,
            "created_at": now,
            "execute_at": scheduled_time,
            "command": command_name,
            "args": content,
            "full_command": f"{self.bot.command_prefix}{command_name} {content}",
            "mentions": [mention.id for mention in ctx.message.mentions],
            "role_mentions": [mention.id for mention in ctx.message.role_mentions],
        }

        out = (
            f"Scheduled command: `{command_name}`\n"
            f"Arguments: {content}\n"
            f"To occur at: {timestamp}"
        )
        await send_message_and_file(
            channel=ctx.channel, title="Schedule successful!", message=out
        )

        self.scheduled_tasks[str(ctx.message.id)] = scheduled_task
        await self.save_scheduled_tasks()

    @commands.command(
        name="unschedule",
        brief="Unschedule a scheduled command",
        description="Task IDs can be found from calling .view_schedule",
        help="""
    Usage:
    .unschedule <task_id>
    .unschedule all - remove all scheduled tasks
        """,
    )
    @perms.gm_only("unschedule a command")
    async def unschedule(self, ctx: commands.Context, task_id: str):
        task_id = task_id.strip()

        if task_id == "all":
            gid = ctx.guild.id
            ids = [
                id
                for id, task in self.scheduled_tasks.items()
                if task["guild_id"] == gid
            ]
            for id in ids:
                del self.scheduled_tasks[id]
                await self.save_scheduled_tasks()

            await send_message_and_file(
                channel=ctx.channel,
                message=f"Deleted all {len(ids)} scheduled tasks for this guild.",
            )
            return

        try:
            task = self.scheduled_tasks[task_id]
            del self.scheduled_tasks[task_id]
            await self.save_scheduled_tasks()
            await send_message_and_file(
                channel=ctx.channel,
                message=f"Deleted scheduled task: {task['command']} for {task['execute_at']}",
            )
        except KeyError:
            await send_message_and_file(
                channel=ctx.channel,
                title="Error!",
                message=f"No scheduled task correlates with the ID: {task_id}",
                embed_colour=ERROR_COLOUR,
            )

    @commands.command(
        name="view_schedule",
        brief="View scheduled commands.",
    )
    @perms.gm_only("view command schedule")
    async def view_schedule(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            return

        guild_tasks = {
            id: task
            for id, task in self.scheduled_tasks.items()
            if task["guild_id"] == guild.id
        }
        guild_tasks = dict(
            sorted(guild_tasks.items(), key=lambda pair: pair[1]["execute_at"])
        )

        out = ["(sorted by soonest)"]
        for id, task in guild_tasks.items():
            user = self.bot.get_user(task["invoking_user_id"])
            s = f"Task ID = `{id}`:\n- [{user.mention if user else task['invoking_user_name']}] -> `{task['command']}` at {task['execute_at']}"
            if len(task["args"]) != 0:
                s += f"\n  - Arguments: {task['args']}"

            out.append(s)

        out = "\n".join(out)

        await send_message_and_file(
            channel=ctx.channel, title=f"Scheduled tasks for {guild.name}", message=out
        )

    @tasks.loop(seconds=LOOP_FREQUENCY_SECONDS)
    async def process_scheduled_tasks(self):
        # TODO: Clean up reporting and add logging for deserialisation errors
        now = datetime.datetime.now(datetime.timezone.utc)
        due = {
            id: task
            for id, task in self.scheduled_tasks.items()
            if task["execute_at"] <= now
        }

        for id, task in due.items():
            channel_id = task["channel_id"]
            channel = self.bot.get_channel(channel_id)
            if not channel:
                del self.scheduled_tasks[id]
                await self.save_scheduled_tasks()
                continue

            full_command = task["full_command"]

            # skip over stale tasks, suspected change of state not worthy of continuing automatic behaviour
            # guard in case bot goes down for extended periods
            delta = now - task["execute_at"]
            if delta > MAX_DELAY:
                logger.warning(
                    f"Skipping stale task {id}: Could not handle on time. (missed by '{now-task['execute_at']}') which is greater than maximum allowed time '{MAX_DELAY}'"
                )
                await send_message_and_file(
                    channel=channel,
                    message=f"Skipping stale task {id}: Could not handle on time (Expected: {task['execute_at']})\nTask: {full_command}",
                    embed_colour=ERROR_COLOUR,
                )
                del self.scheduled_tasks[id]
                await self.save_scheduled_tasks()
                continue

            user = self.bot.get_user(task["invoking_user_id"])
            if user is None:
                await send_message_and_file(
                    channel=channel,
                    message=f"Skipping task {id}: Could not find invoking user\nTask: {full_command}",
                    embed_colour=ERROR_COLOUR,
                )
                del self.scheduled_tasks[id]
                await self.save_scheduled_tasks()
                continue

            out = (
                f"Command: {task['command']}\n"
                f"Invoking: {task['full_command']}\n"
                f"Scheduled by: {user.mention}\n"
                f"Scheduled at: {task['created_at']}"
            )
            await send_message_and_file(
                channel=channel, title="Executing scheduled command!", message=out
            )

            mentions_users = []
            for user_id in task["mentions"]:
                if mentioned_user := self.bot.get_user(user_id):
                    mentions_users.append(
                        self.get_payload_user_from_user(mentioned_user)
                    )

            message = Message(
                state=self.bot._connection,
                channel=channel,
                data={
                    "id": task["invoking_msg_id"],
                    "author": self.get_payload_user_from_user(user),
                    "content": task["full_command"],
                    "timestamp": task["execute_at"],
                    "edited_timestamp": None,
                    "tts": False,
                    "mention_everyone": False,
                    "mentions": mentions_users,
                    "mention_roles": task["role_mentions"],
                    "attachments": [],
                    "embeds": [],
                    "pinned": False,
                    "type": 1,
                    "channel_id": channel.id,
                },
            )

            # delete task immediately to prevent long tasks carrying over to new loops
            del self.scheduled_tasks[id]
            await self.save_scheduled_tasks()
            try:
                log_command_no_ctx(
                    logger,
                    task["full_command"],
                    channel.guild.name,
                    channel.name,
                    user.name,
                    f"Executing command scheduled by '{task['invoking_user_name']}' at {task['created_at']}",
                )

                await self.bot.process_commands(message)
            except Exception as e:
                await channel.send(
                    f"Failure to invoke scheduled command.\nCommand: `{task['full_command']}`\nScheduled at: {task['created_at']}"
                )

                user = self.bot.get_user(task["invoking_user_id"])
                if user:
                    await channel.send(f"Alert: {user.mention}")

                raise e

    @process_scheduled_tasks.before_loop
    async def before_process_scheduled_tasks(self):
        await self.bot.wait_until_ready()

    async def save_scheduled_tasks(self):
        logger.info(f"Saving {len(self.scheduled_tasks)} stored scheduled tasks")
        with open(self.scheduled_storage, "w") as f:
            curr_tasks = deepcopy(self.scheduled_tasks)
            for _, task in curr_tasks.items():
                task["created_at"] = task["created_at"].isoformat()
                task["execute_at"] = task["execute_at"].isoformat()

            json.dump(curr_tasks, f)

    @staticmethod
    def get_payload_user_from_user(user: User):
        return {
            "id": user.id,
            "username": user.name,
            "discriminator": user.discriminator,
            "avatar": user.avatar.url if user.avatar else None,
            "global_name": user.global_name,
            "bot": user.bot,
            "system": user.system,
            "mfa_enabled": False,
            "locale": "",
            "verified": True,
            "email": None,
            "flags": 0,
            "premium_type": 0,
            "public_flags": user.public_flags,
        }


async def setup(bot):
    cog = ScheduleCog(bot)
    await bot.add_cog(cog)
