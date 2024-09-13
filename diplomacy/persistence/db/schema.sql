CREATE TABLE IF NOT EXISTS boards (
    board_id int,
    phase text,
    map_file text,
    PRIMARY KEY (board_id, phase));
CREATE TABLE IF NOT EXISTS players (
    board_id int,
    player_name text,
    color varchar(6),
    PRIMARY KEY (board_id, player_name),
    FOREIGN KEY (board_id) REFERENCES boards (board_id));
CREATE TABLE IF NOT EXISTS provinces (
    board_id int,
    phase text,
    province_name text,
    owner text,
    core text,
    half_core text,
    PRIMARY KEY (board_id, phase, province_name),
    FOREIGN KEY (board_id, phase) REFERENCES boards (board_id, phase),
    FOREIGN KEY (board_id, owner) REFERENCES players (board_id, player_name),
    FOREIGN KEY (board_id, core) REFERENCES players (board_id, player_name),
    FOREIGN KEY (board_id, half_core) REFERENCES players (board_id, player_name));
CREATE TABLE IF NOT EXISTS units (
    board_id int,
    phase text,
    location text,
    is_dislodged boolean,
    owner text,
    is_army boolean,
    order_type text,
    order_destination text,
    order_source text,
    PRIMARY KEY (board_id, phase, location, is_dislodged),
    FOREIGN KEY (board_id, phase) REFERENCES boards (board_id, phase),
    FOREIGN KEY (board_id, phase, location) REFERENCES provinces (board_id, phase, province_name),
    FOREIGN KEY (board_id, owner) REFERENCES players (board_id, player_name));