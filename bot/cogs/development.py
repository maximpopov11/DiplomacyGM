import logging

import discord
from discord.ext import commands
import random

from bot.config import (
IMPDIP_SERVER_ID,
IMPDIP_BOT_WIZARD_ROLE
)
from bot.bot import DiploGM
from bot import perms
from bot.config import IMPDIP_SERVER_ID
from bot.utils import send_message_and_file
from diplomacy.persistence.manager import Manager

logger = logging.getLogger(__name__)
manager = Manager()


class DevelopmentCog(commands.Cog):
    """
    Superuser features primarily used for Development of the bot
    """
    bot: DiploGM

    def __init__(self, bot: DiploGM):
        self.bot = bot

    @commands.command(hidden=True)
    @perms.superuser_only("show the superuser dashboard")
    async def su_dashboard(self, ctx: commands.Context):

        extensions_body = ""
        for extension in self.bot.get_all_extensions():
            if extension in self.bot.extensions.keys():
                extensions_body += "- :white_check_mark: "
            else:
                extensions_body += "- :x: "
            extensions_body += f"{extension}\n"

        cogs_body = ""
        for cog in self.bot.cogs.keys():
            cogs_body += f"- {cog}\n"

        bot_wizards = self.bot.get_guild(IMPDIP_SERVER_ID).get_role(IMPDIP_BOT_WIZARD_ROLE).members
        footer = random.choice(
            [f"Rather upset at {bot_wizard.nick} >:(" for bot_wizard in bot_wizards]
            + [f"eolhc keeps stabbing me", f"aahoughton, I don't recognise your union!"]
        )

        await send_message_and_file(
            channel=ctx.channel,
            title=f"DiplomacyGM Dashboard",
            fields=[("Extensions", extensions_body), ("Loaded Cogs", cogs_body)],
            footer_content=footer,
        )



async def setup(bot: DiploGM):
    cog = DevelopmentCog(bot)
    await bot.add_cog(cog)

async def teardown(bot: DiploGM):
    pass