import logging
import os
from dotenv.main import load_dotenv
load_dotenv()
from bot import bot

log_level = logging.getLevelNamesMapping().get(os.getenv("log_level", "INFO"))
if not log_level:
    log_level = logging.INFO
logging.basicConfig(level=log_level)
if __name__ == '__main__':
    bot.run()
