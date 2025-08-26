CREATE TABLE IF NOT EXISTS boards (
    board_id int,
    phase text,
    data_file text,
    fish int,
	name text,
    PRIMARY KEY (board_id, phase));
CREATE TABLE IF NOT EXISTS players (
    board_id int,
    player_name text,
    color varchar(6),
    liege text,
    points int,
    discord_id text,
    PRIMARY KEY (board_id, player_name),
    FOREIGN KEY (board_id, liege) REFERENCES players (board_id, player_name),
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
CREATE TABLE IF NOT EXISTS retreat_options (
    board_id int,
    phase text,
    origin text,
    retreat_loc text,
    PRIMARY KEY (board_id, phase, origin, retreat_loc),
    FOREIGN KEY (board_id, phase) REFERENCES boards (board_id, phase),
    FOREIGN KEY (board_id, phase, origin) REFERENCES provinces (board_id, phase, province_name),
    FOREIGN KEY (board_id, phase, retreat_loc) REFERENCES provinces (board_id, phase, province_name));
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
    failed_order boolean,
    PRIMARY KEY (board_id, phase, location, is_dislodged),
    FOREIGN KEY (board_id, phase) REFERENCES boards (board_id, phase),
    FOREIGN KEY (board_id, phase, location) REFERENCES provinces (board_id, phase, province_name),
    FOREIGN KEY (board_id, owner) REFERENCES players (board_id, player_name),
    FOREIGN KEY (board_id, phase, location) REFERENCES retreat_options (board_id, phase, origin));
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
);

CREATE TABLE IF NOT EXISTS vassal_orders (
    board_id int,
    phase text,
    player text,
    target_player text,
    order_type text,
    PRIMARY KEY (board_id, phase, player, target_player),
    FOREIGN KEY (board_id, player) REFERENCES players (board_id, player),
    FOREIGN KEY (board_id, target_player) REFERENCES players (board_id, player)
);
CREATE TABLE IF NOT EXISTS spec_requests (
	request_id INTEGER PRIMARY KEY AUTOINCREMENT,
	server_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	role_id INTEGER NOT NULL,
	UNIQUE (server_id, user_id) -- only one approved request can be stored per server
);
