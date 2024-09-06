CREATE TABLE IF NOT EXISTS boards (
    board_id int,
    map_file text,
    phase text,
    PRIMARY KEY (board_id));
CREATE TABLE IF NOT EXISTS players (
    board_id int,
    player_name text,
    color varchar(6),
    PRIMARY KEY (board_id, player_name),
    FOREIGN KEY (board_id) REFERENCES boards (board_id));
CREATE TABLE IF NOT EXISTS provinces (
    board_id int,
    province_name text,
    owner text,
    core text,
    half_core text,
    PRIMARY KEY (board_id, province_name),
    FOREIGN KEY (board_id) REFERENCES boards (board_id),
    FOREIGN KEY (board_id, owner) REFERENCES players (board_id, player_name),
    FOREIGN KEY (board_id, core) REFERENCES players (board_id, player_name),
    FOREIGN KEY (board_id, half_core) REFERENCES players (board_id, player_name));
CREATE TABLE IF NOT EXISTS units (
    board_id int,
    location text,
    is_dislodged boolean,
    owner text,
    is_army boolean,
    PRIMARY KEY (board_id, location, is_dislodged),
    FOREIGN KEY (board_id) REFERENCES boards (board_id),
    FOREIGN KEY (board_id, location) REFERENCES provinces (board_id, province_name),
    FOREIGN KEY (board_id, owner) REFERENCES players (board_id, player_name));