from discord.ext import commands


class SampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    cog = SampleCog(bot)
    await bot.add_cog(cog)
