import logging
import os

from bot import bot
from test import functional_test

log_level = logging.getLevelNamesMapping().get(os.getenv("log_level", "INFO"))
if not log_level:
    log_level = logging.INFO
logging.basicConfig(level=log_level)
# from test import mapper_test

# mapper_test.run()

bot.run()

# from test import db_test, functional_test

# functional_test.run()
