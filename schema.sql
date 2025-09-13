
CREATE TABLE error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    endpoint TEXT,
    method TEXT,
    error_message TEXT NOT NULL,
    traceback TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);