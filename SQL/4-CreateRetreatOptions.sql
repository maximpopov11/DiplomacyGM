CREATE TABLE retreat_options (
    board_id int,
    phase text,
    origin text,
    retreat_loc text,
    PRIMARY KEY (board_id, phase, origin, retreat_loc),
    FOREIGN KEY (board_id, phase, origin) REFERENCES provinces (board_id, phase, province_name),
    FOREIGN KEY (board_id, phase, retreat_loc) REFERENCES provinces (board_id, phase, province_name));

ALTER TABLE units
ADD FOREIGN KEY (board_id, phase, province_name) REFERENCES retreat_options (board_id, phase, origin);