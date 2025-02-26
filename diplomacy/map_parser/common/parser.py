import copy
import logging
from diplomacy.map_parser.common.result import ParserResult
from diplomacy.map_parser.vector.vector import Parser
from diplomacy.persistence.board import Board

logger = logging.getLogger(__name__)
    
parsers: dict[str, ParserResult] = {}

def parse_board(name: str) -> Board:
    if name not in parsers:
        logger.info(f"Creating new Parser for board named {name}")
        parsers[name] = Parser(name)
    return parsers[name].parse().make_board()
