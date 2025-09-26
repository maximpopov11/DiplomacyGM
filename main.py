import asyncio
import logging
import os
from dotenv.main import load_dotenv

load_dotenv()
from bot.bot import bot

log_level = logging.getLevelNamesMapping().get(os.getenv("log_level", "INFO"))
if not log_level:
    log_level = logging.INFO
logging.basicConfig(level=log_level)


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("The DISCORD_TOKEN environment variable is not set")

    # NOTE: bot instantiation can occur here if all commands are spun off into cogs
    # importing a variable created on import and located in ./bot/bot.py seems messy
    bot.run(token)


if __name__ == "__main__":
    main()
