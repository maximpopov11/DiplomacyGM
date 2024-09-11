import logging
import os

from bot import bot
from test import functional_test

log_level = None#logging.getLevelNamesMapping().get(os.getenv("log_level", "INFO"))
if not log_level:
    log_level = logging.INFO
logging.basicConfig(level=log_level)
# from test import mapper_test

# mapper_test.run()

bot.run()

# from test import db_test, functional_test

# functional_test.run()

# TODO: priorities: (!), <game starts here>, (QOL), <re-organize TODOs/FIXMEs>, (DB), (BETA)

# TODO: (QOL) update readme (how to use bot)

# TODO: (DB) setup DB and test db write & db read
# TODO: (DB) assert that the DB is backed up (needs to be a current up-to-date backup)
# TODO: (DB) ensure resiliency to all errors & log

# TODO: (BETA) sandbox would be great
# TODO: (BETA) some files (read vector.py) are really bad, clean them up
# TODO: (BETA): import by file instead of by thing in file?
# TODO: (BETA) me only command for editing all game map state without permanence restriction (ex. province adjacency)
# TODO: (BETA) don't rely on PyDip, it's so much easier to update things when I own all of the code and write it pretty
# TODO: (BETA) add requirements.txt
# TODO: (BETA) clean up configs
# TODO: (BETA) support SVGs with minimal overhead
# TODO: (BETA) support raster images
# TODO: (BETA) add classic map example & update readme
