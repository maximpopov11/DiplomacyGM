-- Step 1: Create the new table
CREATE TABLE boards_new (
    board_id INTEGER,
    phase TEXT,
    data_file TEXT,
    fish INTEGER,
    PRIMARY KEY (board_id, phase)
);

-- Step 2: Copy data from the old table to the new one
INSERT INTO boards_new (board_id, phase, data_file, fish)
SELECT board_id, phase, map_file, fish FROM boards;

-- Step 3: Drop the old table
DROP TABLE boards;

-- Step 4: Rename the new table to 'boards'
ALTER TABLE boards_new RENAME TO boards;

UPDATE boards
SET data_file = 'impdip.json';