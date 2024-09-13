DROP TABLE IF EXISTS boards_tmp;
DROP TABLE IF EXISTS players_tmp;
DROP TABLE IF EXISTS provinces_tmp;
DROP TABLE IF EXISTS units_tmp;

CREATE TABLE boards_tmp AS SELECT * FROM boards;
CREATE TABLE players_tmp AS SELECT * FROM players;
CREATE TABLE provinces_tmp AS SELECT * FROM provinces;
CREATE TABLE units_tmp AS SELECT * FROM units;

ALTER TABLE provinces_tmp ADD COLUMN phase text;
ALTER TABLE units_tmp ADD COLUMN phase text;

UPDATE provinces_tmp SET phase='Spring Moves';
UPDATE units_tmp SET phase='Spring Moves';

DROP TABLE boards;
DROP TABLE players;
DROP TABLE provinces;
DROP TABLE units;

CREATE TABLE boards (
    board_id int,
    phase text,
    map_file text,
    PRIMARY KEY (board_id, phase));
CREATE TABLE players (
    board_id int,
    player_name text,
    color varchar(6),
    PRIMARY KEY (board_id, player_name),
    FOREIGN KEY (board_id) REFERENCES boards (board_id));
CREATE TABLE provinces (
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
CREATE TABLE units (
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

INSERT INTO boards SELECT board_id, phase, map_file FROM boards_tmp;
INSERT INTO players SELECT board_id, player_name, color FROM players_tmp;
INSERT INTO provinces SELECT board_id, phase, province_name, owner, core, half_core FROM provinces_tmp;
INSERT INTO units SELECT board_id, phase, location, is_dislodged, owner, is_army, order_type, order_destination, order_source FROM units_tmp;
