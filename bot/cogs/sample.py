import logging

from discord.ext import commands

from diplomacy.persistence.manager import Manager

logger = logging.getLogger(__name__)
manager = Manager()


class SampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    cog = SampleCog(bot)
    await bot.add_cog(cog)
