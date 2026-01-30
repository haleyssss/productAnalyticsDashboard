CREATE TABLE IF NOT EXISTS events (
  user_id INTEGER NOT NULL,
  event_name TEXT NOT NULL,
  event_time TIMESTAMP NOT NULL,
  platform TEXT,
  acquisition_source TEXT
);
