import asyncio
from dotenv.main import load_dotenv
import logging
import os

from discord import Intents

from bot.bot import DiploGM

load_dotenv()

log_level = logging.INFO
match os.getenv("log_level", logging.INFO):
    case "ERROR":
        log_level = logging.ERROR
    case "WARN" | "WARNING":
        log_level = logging.WARNING
    case "DEBUG":
        log_level = logging.DEBUG


logging.basicConfig(
    format="%(asctime)-15s | %(levelname)-7s: | %(filename)-16s (line %(lineno)-4d) | %(message)s",
    level=log_level,
)

logger = logging.getLogger(__name__)


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("The DISCORD_TOKEN environment variable is not set")

    intents = Intents.default()
    intents.message_content = True
    intents.members = True
    bot = DiploGM(
        command_prefix=os.getenv("command_prefix", default="."), intents=intents
    )

    async with bot:
        try:
            await bot.start(token)
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.warning("Interrupt detected, attempting close...")
        finally:
            if not bot.is_closed():
                await bot.close()

            logger.info("Bot has shut down :)")


if __name__ == "__main__":
    asyncio.run(main())
