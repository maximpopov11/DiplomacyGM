from dotenv.main import load_dotenv
import logging
import os

from discord import Intents

from bot.bot import DiploGM

load_dotenv()

log_level = logging.getLevelNamesMapping().get(os.getenv("log_level", "INFO"))
if not log_level:
    log_level = logging.INFO
logging.basicConfig(
    format="%(asctime)-15s | %(levelname)-7s | %(filename)-16s (line %(lineno)-4d) | %(message)s",
    level=log_level,
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    intents = Intents.default()
    intents.message_content = True
    intents.members = True
    bot = DiploGM(
        command_prefix=os.getenv("command_prefix", default="."), intents=intents
    )

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("The DISCORD_TOKEN environment variable is not set")

    bot.run(token)
