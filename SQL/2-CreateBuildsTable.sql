CREATE TABLE IF NOT EXISTS builds(
    board_id int,
    phase text,
    player text,
    location text,
    is_build boolean,
    is_army boolean,
    PRIMARY KEY (board_id, phase, player, location),
    FOREIGN KEY (board_id, phase) REFERENCES boards (board_id, phase),
    FOREIGN KEY (board_id, player) REFERENCES players (board_id, player_name),
    FOREIGN KEY (board_id, phase, location) REFERENCES provinces (board_id, phase, province_name)
)