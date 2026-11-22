package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
)

const maxChats = 10
const maxQueue = 100

type chat struct {
	ID uuid.UUID `json:"id"`
	target
	Title   string    `json:"title"`
	Status  string    `json:"status"`
	Created time.Time `json:"created_at"`
}

type source struct {
	Ref            int    `json:"ref"`
	ChunkID        string `json:"chunk_id"`
	DocumentID     string `json:"document_id"`
	Title          string `json:"title"`
	URL            string `json:"source_url"`
	Distribution   string `json:"distribution"`
	Section        string `json:"section"`
	Command        string `json:"command"`
	Text           string `json:"text"`
	PackageVersion string `json:"package_version"`
	CollectedAt    string `json:"collected_at,omitempty"`
}

type sourceCard struct {
	Ref          int    `json:"ref"`
	ChunkID      string `json:"chunk_id"`
	DocumentID   string `json:"document_id"`
	Title        string `json:"title"`
	URL          string `json:"source_url"`
	Distribution string `json:"distribution"`
	Section      string `json:"section"`
}

type message struct {
	ID            uuid.UUID    `json:"id"`
	Role          string       `json:"role"`
	Content       string       `json:"content"`
	Status        string       `json:"status"`
	Sources       []sourceCard `json:"sources"`
	Created       time.Time    `json:"created_at"`
	CorpusVersion string       `json:"corpus_version,omitempty"`
	FinishReason  string       `json:"finish_reason,omitempty"`
	Error         string       `json:"error,omitempty"`
}

const columns = "id,role,content,status,sources,created_at,corpus_version,finish_reason,error"

func readMessage(row pgx.Row) (message, error) {
	var item message
	var sources []sourceCard
	err := row.Scan(&item.ID, &item.Role, &item.Content, &item.Status, &sources, &item.Created, &item.CorpusVersion, &item.FinishReason, &item.Error)
	item.Sources = sources
	return item, err
}

func (s *server) listChats(w http.ResponseWriter, r *http.Request, a account, _ uuid.UUID) {
	rows, err := s.db.Query(r.Context(), `SELECT c.id,c.distribution,c.title,c.created_at,
		COALESCE((SELECT m.status FROM messages m WHERE m.chat_id=c.id AND m.status IN ('queued','generating')), 'idle')
		FROM chats c WHERE c.account_id=$1 ORDER BY c.created_at DESC`, a.ID)
	if err != nil {
		serverError(w, err)
		return
	}
	defer rows.Close()
	items := make([]chat, 0)
	for rows.Next() {
		var c chat
		if err := rows.Scan(&c.ID, &c.Distribution, &c.Title, &c.Created, &c.Status); err != nil {
			serverError(w, err)
			return
		}
		items = append(items, c)
	}
	if err := rows.Err(); err != nil {
		serverError(w, err)
		return
	}
	jsonReply(w, 200, map[string]any{"items": items})
}

func (s *server) createChat(w http.ResponseWriter, r *http.Request, a account, _ uuid.UUID) {
	var input struct {
		target
		Title         string `json:"title"`
		LegacyRelease string `json:"release,omitempty"`
	}
	if !readJSON(w, r, &input) {
		return
	}
	input.Title = strings.TrimSpace(input.Title)
	if input.Title == "" {
		input.Title = "Новый чат"
	}
	if utf8.RuneCountInString(input.Title) > 120 || strings.ContainsRune(input.Title, 0) {
		fail(w, 400, "INVALID_TITLE", "Название чата должно содержать до 120 символов.")
		return
	}
	info, err := s.corpus(r.Context())
	if err != nil {
		serverError(w, err)
		return
	}
	supported := false
	for _, d := range info.Distributions {
		if d.ID == input.Distribution {
			supported = true
			break
		}
	}
	if !supported {
		fail(w, 422, "UNSUPPORTED_TARGET", "Нет проверенного корпуса для выбранной системы.")
		return
	}

	ctx := r.Context()
	tx, err := s.db.Begin(ctx)
	if err != nil {
		serverError(w, err)
		return
	}
	defer tx.Rollback(context.Background())
	if err := lockAccount(ctx, tx, a.ID); err != nil {
		serverError(w, err)
		return
	}
	var count int
	if err := tx.QueryRow(ctx, "SELECT count(*) FROM chats WHERE account_id=$1", a.ID).Scan(&count); err != nil {
		serverError(w, err)
		return
	}
	if count >= maxChats {
		fail(w, 409, "CHAT_LIMIT", "У вас уже десять чатов. Удалите один, чтобы создать новый.")
		return
	}
	item := chat{ID: uuid.New(), target: input.target, Title: input.Title, Status: "idle"}
	err = tx.QueryRow(ctx, `INSERT INTO chats (id,account_id,distribution,title) VALUES ($1,$2,$3,$4)
		RETURNING created_at`, item.ID, a.ID, item.Distribution, item.Title).Scan(&item.Created)
	if err == nil {
		err = tx.Commit(ctx)
	}
	if err != nil {
		serverError(w, err)
		return
	}
	jsonReply(w, 201, item)
}

func lockAccount(ctx context.Context, tx pgx.Tx, id uuid.UUID) error {
	var locked uuid.UUID
	return tx.QueryRow(ctx, "SELECT id FROM accounts WHERE id=$1 FOR UPDATE", id).Scan(&locked)
}

func (s *server) deleteChat(w http.ResponseWriter, r *http.Request, a account, _ uuid.UUID) {
	id, ok := pathUUID(w, r, "chat_id")
	if !ok {
		return
	}
	ctx := r.Context()
	tx, err := s.db.Begin(ctx)
	if err != nil {
		serverError(w, err)
		return
	}
	defer tx.Rollback(context.Background())
	if err := lockAccount(ctx, tx, a.ID); err != nil {
		serverError(w, err)
		return
	}
	var busy bool
	err = tx.QueryRow(ctx, `SELECT EXISTS (SELECT 1 FROM messages WHERE chat_id=c.id AND status IN ('queued','generating'))
		FROM chats c WHERE id=$1 AND account_id=$2`, id, a.ID).Scan(&busy)
	if errors.Is(err, pgx.ErrNoRows) {
		fail(w, 404, "CHAT_NOT_FOUND", "Чат не найден.")
		return
	}
	if err != nil {
		serverError(w, err)
		return
	}
	if busy {
		fail(w, 409, "CHAT_BUSY", "Остановите задание перед удалением чата.")
		return
	}
	if _, err = tx.Exec(ctx, "DELETE FROM chats WHERE id=$1 AND account_id=$2", id, a.ID); err == nil {
		err = tx.Commit(ctx)
	}
	if err != nil {
		serverError(w, err)
		return
	}
	w.WriteHeader(204)
}

func (s *server) listMessages(w http.ResponseWriter, r *http.Request, a account, _ uuid.UUID) {
	chatID, ok := pathUUID(w, r, "chat_id")
	if !ok {
		return
	}
	ctx := r.Context()
	tx, err := s.db.BeginTx(ctx, pgx.TxOptions{AccessMode: pgx.ReadOnly, IsoLevel: pgx.RepeatableRead})
	if err != nil {
		serverError(w, err)
		return
	}
	defer tx.Rollback(context.Background())
	var exists bool
	err = tx.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM chats WHERE id=$1 AND account_id=$2)", chatID, a.ID).Scan(&exists)
	if err != nil {
		serverError(w, err)
		return
	}
	if !exists {
		fail(w, 404, "CHAT_NOT_FOUND", "Чат не найден.")
		return
	}
	rows, err := tx.Query(ctx, "SELECT "+columns+" FROM messages WHERE chat_id=$1 AND account_id=$2 ORDER BY seq", chatID, a.ID)
	if err != nil {
		serverError(w, err)
		return
	}
	defer rows.Close()
	items := make([]message, 0)
	for rows.Next() {
		m, err := readMessage(rows)
		if err != nil {
			rows.Close()
			serverError(w, err)
			return
		}
		items = append(items, m)
	}
	if err := rows.Err(); err != nil {
		serverError(w, err)
		return
	}
	if err := tx.Commit(ctx); err != nil {
		serverError(w, err)
		return
	}
	jsonReply(w, 200, map[string]any{"items": items})
}

type question struct {
	Content   string    `json:"content"`
	Stream    bool      `json:"stream"`
	RequestID uuid.UUID `json:"client_request_id"`
}

type rejected struct {
	status  int
	problem problem
}

func (e *rejected) Error() string { return e.problem.Code }

func reject(status int, code, text string) *rejected {
	return &rejected{status: status, problem: problem{Code: code, Message: text}}
}

func (s *server) enqueue(ctx context.Context, owner, chatID uuid.UUID, q question) (message, error) {
	tx, err := s.db.Begin(ctx)
	if err != nil {
		return message{}, err
	}
	defer tx.Rollback(context.Background())
	if err := lockAccount(ctx, tx, owner); err != nil {
		return message{}, err
	}
	var title string
	err = tx.QueryRow(ctx, "SELECT title FROM chats WHERE id=$1 AND account_id=$2", chatID, owner).Scan(&title)
	if errors.Is(err, pgx.ErrNoRows) {
		return message{}, reject(404, "CHAT_NOT_FOUND", "Чат не найден.")
	}
	if err != nil {
		return message{}, err
	}
	var existing uuid.UUID
	err = tx.QueryRow(ctx, "SELECT id FROM messages WHERE chat_id=$1 AND client_request_id=$2", chatID, q.RequestID).Scan(&existing)
	if err == nil {
		rejection := reject(409, "REQUEST_EXISTS", "Вопрос уже принят.")
		rejection.problem.MessageID = &existing
		return message{}, rejection
	}
	if !errors.Is(err, pgx.ErrNoRows) {
		return message{}, err
	}
	var busy bool
	err = tx.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM messages WHERE chat_id=$1 AND status IN ('queued','generating'))", chatID).Scan(&busy)
	if err != nil {
		return message{}, err
	}
	if busy {
		return message{}, reject(409, "CHAT_BUSY", "В этом чате уже есть ожидающий или активный вопрос.")
	}

	if _, err = tx.Exec(ctx, "SELECT pg_advisory_xact_lock(780322)"); err != nil {
		return message{}, err
	}
	var queued int
	if err = tx.QueryRow(ctx, "SELECT count(*) FROM messages WHERE status='queued'").Scan(&queued); err != nil {
		return message{}, err
	}
	if queued >= maxQueue {
		return message{}, reject(429, "QUEUE_FULL", "Очередь заполнена. Повторите попытку позже.")
	}

	_, err = tx.Exec(ctx, `INSERT INTO messages (id,chat_id,account_id,role,content,status) VALUES ($1,$2,$3,'user',$4,'complete')`,
		uuid.New(), chatID, owner, q.Content)
	if err != nil {
		return message{}, err
	}
	answer, err := readMessage(tx.QueryRow(ctx, `INSERT INTO messages (id,chat_id,account_id,role,status,client_request_id,question)
		VALUES ($1,$2,$3,'assistant','queued',$4,$5) RETURNING `+columns, uuid.New(), chatID, owner, q.RequestID, q.Content))
	if err != nil {
		return message{}, err
	}
	if title == "Новый чат" {
		newTitle := limitRunes(strings.Join(strings.Fields(q.Content), " "), 70)
		if _, err = tx.Exec(ctx, "UPDATE chats SET title=$1 WHERE id=$2", newTitle, chatID); err != nil {
			return message{}, err
		}
	}
	return answer, tx.Commit(ctx)
}

func (s *server) sendMessage(w http.ResponseWriter, r *http.Request, a account, _ uuid.UUID) {
	chatID, ok := pathUUID(w, r, "chat_id")
	if !ok {
		return
	}
	var q question
	if !readJSON(w, r, &q) {
		return
	}
	q.Content = strings.TrimSpace(q.Content)
	if q.RequestID == uuid.Nil || q.Content == "" || utf8.RuneCountInString(q.Content) > 4000 || strings.ContainsRune(q.Content, 0) {
		fail(w, 400, "INVALID_QUESTION", "Вопрос должен содержать от 1 до 4000 символов и иметь UUID запроса.")
		return
	}
	answer, err := s.enqueue(r.Context(), a.ID, chatID, q)
	var rejection *rejected
	if errors.As(err, &rejection) {
		jsonReply(w, rejection.status, errorReply{rejection.problem})
		return
	}
	if err != nil {
		serverError(w, err)
		return
	}
	s.notify()
	if q.Stream {
		s.stream(w, r, answer)
		return
	}
	jsonReply(w, 202, answer)
}

func (s *server) cancelMessage(w http.ResponseWriter, r *http.Request, a account, _ uuid.UUID) {
	chatID, ok := pathUUID(w, r, "chat_id")
	if !ok {
		return
	}
	messageID, ok := pathUUID(w, r, "message_id")
	if !ok {
		return
	}
	cmd, err := s.db.Exec(r.Context(), `UPDATE messages SET cancel_requested = cancel_requested OR status IN ('queued','generating'),
		finish_reason = CASE WHEN status='queued' THEN 'cancelled' ELSE finish_reason END,
		status = CASE WHEN status='queued' THEN 'cancelled' ELSE status END
		WHERE id=$1 AND chat_id=$2 AND account_id=$3 AND role='assistant'`, messageID, chatID, a.ID)
	if err != nil {
		serverError(w, err)
		return
	}
	if cmd.RowsAffected() == 0 {
		fail(w, 404, "MESSAGE_NOT_FOUND", "Ответ не найден.")
		return
	}
	s.notify()
	w.WriteHeader(204)
}

func (s *server) getSource(w http.ResponseWriter, r *http.Request, a account, _ uuid.UUID) {
	chatID, ok := pathUUID(w, r, "chat_id")
	if !ok {
		return
	}
	messageID, ok := pathUUID(w, r, "message_id")
	if !ok {
		return
	}
	var sources []source
	var version string
	err := s.db.QueryRow(r.Context(), "SELECT sources,corpus_version FROM messages WHERE id=$1 AND chat_id=$2 AND account_id=$3",
		messageID, chatID, a.ID).Scan(&sources, &version)
	if err != nil && !errors.Is(err, pgx.ErrNoRows) {
		serverError(w, err)
		return
	}
	for _, item := range sources {
		if item.ChunkID == r.PathValue("chunk_id") {
			jsonReply(w, 200, struct {
				source
				Version string `json:"corpus_version"`
			}{item, version})
			return
		}
	}
	fail(w, 404, "SOURCE_NOT_FOUND", "Источник не найден.")
}

func event(w http.ResponseWriter, kind string, value any) error {
	encoded, err := json.Marshal(value)
	if err != nil {
		return err
	}
	if _, err = fmt.Fprintf(w, "event: %s\ndata: %s\n\n", kind, encoded); err != nil {
		return err
	}
	return http.NewResponseController(w).Flush()
}

func (s *server) stream(w http.ResponseWriter, r *http.Request, initial message) {
	ctx := r.Context()
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("X-Accel-Buffering", "no")
	state := initial.Status
	if event(w, "status", map[string]any{"message_id": initial.ID, "status": state}) != nil {
		return
	}
	ticker := time.NewTicker(250 * time.Millisecond)
	defer ticker.Stop()
	heartbeat := time.NewTicker(10 * time.Second)
	defer heartbeat.Stop()
	last := ""
	sentSources := false
	for {
		select {
		case <-ctx.Done():
			return
		case <-heartbeat.C:
			if _, err := ioWriteKeepalive(w); err != nil {
				return
			}
		case <-ticker.C:
			item, err := readMessage(s.db.QueryRow(ctx, "SELECT "+columns+" FROM messages WHERE id=$1", initial.ID))
			if err != nil {
				_ = event(w, "error", problem{Code: "STREAM_ERROR", Message: "Состояние ответа недоступно."})
				return
			}
			if state != item.Status && item.Status == "generating" {
				if event(w, "status", map[string]any{"message_id": item.ID, "status": item.Status}) != nil {
					return
				}
			}
			state = item.Status
			if !sentSources && item.CorpusVersion != "" {
				if event(w, "sources", map[string]any{"message_id": item.ID, "corpus_version": item.CorpusVersion, "sources": item.Sources}) != nil {
					return
				}
				sentSources = true
			}
			if len(item.Content) > len(last) && strings.HasPrefix(item.Content, last) {
				if event(w, "token", map[string]string{"delta": item.Content[len(last):]}) != nil {
					return
				}
				last = item.Content
			}
			switch item.Status {
			case "complete", "cancelled":
				_ = event(w, "done", map[string]any{"message_id": item.ID, "finish_reason": item.FinishReason})
				return
			case "error":
				_ = event(w, "error", problem{Code: "GENERATION_FAILED", Message: item.Error})
				return
			}
		}
	}
}

func ioWriteKeepalive(w http.ResponseWriter) (int, error) {
	n, err := fmt.Fprint(w, ": heartbeat\n\n")
	if err == nil {
		err = http.NewResponseController(w).Flush()
	}
	return n, err
}
