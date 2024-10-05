BEGIN TRANSACTION;

CREATE TABLE retreat_options (
    board_id int,
    phase text,
    origin text,
    retreat_loc text,
    PRIMARY KEY (board_id, phase, origin, retreat_loc),
    FOREIGN KEY (board_id, phase) REFERENCES boards (board_id, phase),
    FOREIGN KEY (board_id, phase, origin) REFERENCES provinces (board_id, phase, province_name),
    FOREIGN KEY (board_id, phase, retreat_loc) REFERENCES provinces (board_id, phase, province_name));

CREATE TABLE new_units (
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
    FOREIGN KEY (board_id, owner) REFERENCES players (board_id, player_name),
    FOREIGN KEY (board_id, phase, location) REFERENCES retreat_options (board_id, phase, origin));

INSERT INTO new_units (board_id, phase, location, is_dislodged, owner, is_army, order_type, order_destination, order_source)
SELECT board_id, phase, location, is_dislodged, owner, is_army, order_type, order_destination, order_source FROM units;

DROP TABLE units;

ALTER TABLE new_units RENAME to units;

COMMIT;