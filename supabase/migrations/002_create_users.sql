CREATE TABLE IF NOT EXISTS users (
    chat_id BIGINT PRIMARY KEY,
    username TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
