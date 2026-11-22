-- +goose Up
ALTER TABLE chats ALTER COLUMN release SET DEFAULT '';

-- +goose Down
ALTER TABLE chats ALTER COLUMN release DROP DEFAULT;
