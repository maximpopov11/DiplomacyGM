BEGIN TRANSACTION;
ALTER TABLE players RENAME TO players_old;


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

INSERT INTO players (board_id, player_name, color, liege, points, discord_id)
SELECT board_id, player_name, color, NULL, 0, NULL FROM players_old;

DROP TABLE players_old;
COMMIT;