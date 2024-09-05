import logging
import os

from bot import bot
from diplomacy.map_parser.vector.vector import Parser
from diplomacy.persistence.db.database import get_connection

log_level = logging.getLevelNamesMapping().get(os.getenv("log_level", "INFO"))
if not log_level:
    log_level = logging.INFO
logging.basicConfig(level=log_level)
# from test import mapper_test

# mapper_test.run()

# bot.run()

database = get_connection()
print(database.get_boards())
board_parser = Parser()
board = board_parser.parse()
database.save_board(0, board)

# TODO: priorities: (MAP), (ALPHA), <game starts here>, (QOL), (DB), (BETA)

# TODO: (ALPHA) update readme (how to use bot)
# TODO: (ALPHA) conduct testing: test solo, test group, live game test

# TODO: (DB) setup DB and test db write & db read
# TODO: (DB) assert that the DB is backed up (needs to be a current up-to-date backup)

# TODO: (BETA) some files (read vector.py) are really bad, clean them up
# TODO: (BETA): import by file instead of by thing in file?
# TODO: (BETA) me only command for editing all game map state without permanence restriction (ex. province adjacency)
# TODO: (BETA) don't rely on PyDip, it's so much easier to update things when I own all of the code and write it pretty
# TODO: (BETA) add requirements.txt
# TODO: (BETA) clean up configs
# TODO: (BETA) support SVGs with minimal overhead
# TODO: (BETA) support raster images
# TODO: (BETA) add classic map example & update readme
