BEGIN TRANSACTION;

DROP TABLE vassal_orders;

CREATE TABLE vassal_orders (
    board_id int,
    phase text,
    player text,
    target_player text,
    order_type text,
    PRIMARY KEY (board_id, phase, player, target_player),
    FOREIGN KEY (board_id, player) REFERENCES players (board_id, player),
    FOREIGN KEY (board_id, target_player) REFERENCES players (board_id, player)
);

COMMIT;