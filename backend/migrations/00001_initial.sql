-- +goose Up
CREATE TABLE accounts (
    id uuid PRIMARY KEY,
    login text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('user', 'admin'))
);
CREATE TABLE sessions (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL
);
CREATE INDEX sessions_expiry ON sessions (expires_at);
CREATE TABLE chats (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    distribution text NOT NULL,
    release text NOT NULL,
    title text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (id, account_id)
);
CREATE INDEX chats_account ON chats (account_id, created_at DESC);
CREATE TABLE messages (
    seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id uuid NOT NULL UNIQUE,
    chat_id uuid NOT NULL,
    account_id uuid NOT NULL,
    role text NOT NULL CHECK (role IN ('user', 'assistant')),
    content text NOT NULL DEFAULT '',
    status text NOT NULL CHECK (status IN ('queued', 'generating', 'complete', 'cancelled', 'error')),
    client_request_id uuid,
    question text NOT NULL DEFAULT '',
    sources jsonb NOT NULL DEFAULT '[]',
    corpus_version text NOT NULL DEFAULT '',
    finish_reason text NOT NULL DEFAULT '',
    error text NOT NULL DEFAULT '',
    cancel_requested boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (chat_id, account_id) REFERENCES chats(id, account_id) ON DELETE CASCADE,
    UNIQUE (chat_id, client_request_id)
);
CREATE INDEX messages_chat ON messages (chat_id, seq);
CREATE INDEX messages_queue ON messages (seq) WHERE status = 'queued';
CREATE UNIQUE INDEX messages_one_pending_per_chat ON messages (chat_id) WHERE status IN ('queued', 'generating');
CREATE UNIQUE INDEX messages_one_running_per_account ON messages (account_id) WHERE status = 'generating';

-- +goose Down
DROP TABLE messages;
DROP TABLE chats;
DROP TABLE sessions;
DROP TABLE accounts;
