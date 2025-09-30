from discord.ext import commands

from discord import User

from bot import perms
from bot.utils import send_message_and_file


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Returns all shared guilds between DiploGM and user.")
    @perms.mod_only("find mutuals with user")
    async def membership(self, ctx: commands.Context, user: User) -> None:
        guild = ctx.guild
        if not guild:
            return

        out = f"""
    User: {user.mention} [{user.name}]
    Number of Mutual Servers: {len(user.mutual_guilds)}
    ----
    """

        for shared in sorted(user.mutual_guilds, key=lambda g: g.name):
            out += f"{shared.name}\n"

        await send_message_and_file(
            channel=ctx.channel, title=f"User Membership Results", message=out
        )


async def setup(bot):
    cog = ModerationCog(bot)
    await bot.add_cog(cog)
