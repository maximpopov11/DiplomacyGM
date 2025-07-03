BEGIN TRANSACTION;

CREATE TABLE

CREATE TABLE spec_requests (
	request_id INTEGER PRIMARY KEY AUTOINCREMENT,
	server_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	role_id INTEGER NOT NULL,
	UNIQUE (server_id, user_id, role_id)
);


COMMIT;
