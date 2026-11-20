package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
)

type target struct {
	Distribution string `json:"distribution"`
	Release      string `json:"release"`
}

type corpusInfo struct {
	Version       string `json:"corpus_version"`
	Distributions []struct {
		ID       string `json:"id"`
		Label    string `json:"label"`
		Releases []struct {
			ID    string `json:"id"`
			Label string `json:"label"`
		} `json:"releases"`
	} `json:"distributions"`
}

type problem struct {
	Code      string     `json:"code"`
	Message   string     `json:"message"`
	MessageID *uuid.UUID `json:"message_id,omitempty"`
}

type errorReply struct {
	Error problem `json:"error"`
}

func jsonReply(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func fail(w http.ResponseWriter, status int, code, message string) {
	jsonReply(w, status, errorReply{Error: problem{Code: code, Message: message}})
}

func serverError(w http.ResponseWriter, err error) {
	log.Printf("API error: %v", err)
	fail(w, 503, "SERVICE_UNAVAILABLE", "Сервис временно недоступен. Повторите попытку.")
}

func readJSON(w http.ResponseWriter, r *http.Request, dst any) bool {
	body := http.MaxBytesReader(w, r.Body, 32<<10)
	d := json.NewDecoder(body)
	d.DisallowUnknownFields()
	if err := d.Decode(dst); err != nil || d.Decode(new(any)) != io.EOF {
		fail(w, 400, "INVALID_JSON", "Проверьте формат и размер запроса.")
		return false
	}
	return true
}

func pathUUID(w http.ResponseWriter, r *http.Request, name string) (uuid.UUID, bool) {
	id, err := uuid.Parse(r.PathValue(name))
	if err != nil {
		fail(w, 404, "NOT_FOUND", "Запрошенный объект не найден.")
	}
	return id, err == nil
}

func (s *server) headers(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		if !s.sameOrigin(r) {
			fail(w, 403, "ORIGIN_FORBIDDEN", "Запрос пришёл с другого сайта.")
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *server) routes(m *http.ServeMux) {
	m.HandleFunc("GET /api/v1/health", func(w http.ResponseWriter, _ *http.Request) { jsonReply(w, 200, map[string]string{"status": "ok"}) })
	m.HandleFunc("GET /api/v1/ready", s.ready)
	m.HandleFunc("GET /api/v1/corpus", s.getCorpus)
	m.HandleFunc("POST /api/v1/auth/register", s.entry(true))
	m.HandleFunc("POST /api/v1/auth/login", s.entry(false))
	m.HandleFunc("GET /api/v1/auth/me", s.protected("", func(w http.ResponseWriter, _ *http.Request, a account, _ uuid.UUID) { jsonReply(w, 200, a) }))
	m.HandleFunc("POST /api/v1/auth/logout", s.protected("", s.logout))
	m.HandleFunc("GET /api/v1/chats", s.protected("user", s.listChats))
	m.HandleFunc("POST /api/v1/chats", s.protected("user", s.createChat))
	m.HandleFunc("DELETE /api/v1/chats/{chat_id}", s.protected("user", s.deleteChat))
	m.HandleFunc("GET /api/v1/chats/{chat_id}/messages", s.protected("user", s.listMessages))
	m.HandleFunc("POST /api/v1/chats/{chat_id}/messages", s.protected("user", s.sendMessage))
	m.HandleFunc("POST /api/v1/chats/{chat_id}/messages/{message_id}/cancel", s.protected("user", s.cancelMessage))
	m.HandleFunc("GET /api/v1/chats/{chat_id}/messages/{message_id}/sources/{chunk_id}", s.protected("user", s.getSource))
	m.HandleFunc("GET /api/v1/admin/documents", s.protected("admin", s.adminDocuments))
	m.HandleFunc("POST /api/v1/admin/documents", s.protected("admin", s.adminDocuments))
	m.HandleFunc("/api/v1/", func(w http.ResponseWriter, _ *http.Request) {
		fail(w, 404, "NOT_FOUND", "Маршрут не найден.")
	})
}

func (s *server) external(ctx context.Context, method, url, contentType string, body io.Reader) (*http.Response, error) {
	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		return nil, err
	}
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}
	return s.http.Do(req)
}

func (s *server) upstreamJSON(ctx context.Context, url string, body any, output any) error {
	method := http.MethodGet
	var reader io.Reader
	if body != nil {
		encoded, err := json.Marshal(body)
		if err != nil {
			return err
		}
		reader, method = bytes.NewReader(encoded), http.MethodPost
	}
	resp, err := s.external(ctx, method, url, "application/json", reader)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("upstream %s: HTTP %d", url, resp.StatusCode)
	}
	return json.NewDecoder(io.LimitReader(resp.Body, 8<<20)).Decode(output)
}

func (s *server) corpus(ctx context.Context) (corpusInfo, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	var info corpusInfo
	err := s.upstreamJSON(ctx, s.searchURL+"/v1/corpus", nil, &info)
	if err == nil && info.Version == "" {
		err = errors.New("missing corpus version")
	}
	return info, err
}

func (s *server) getCorpus(w http.ResponseWriter, r *http.Request) {
	info, err := s.corpus(r.Context())
	if err != nil {
		serverError(w, err)
		return
	}
	jsonReply(w, 200, info)
}

func (s *server) ready(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 4*time.Second)
	defer cancel()
	if err := s.db.Ping(ctx); err != nil {
		serverError(w, err)
		return
	}
	info, err := s.corpus(ctx)
	if err != nil {
		serverError(w, err)
		return
	}
	var health struct {
		Status string `json:"status"`
	}
	if err := s.upstreamJSON(ctx, s.llmURL+"/health", nil, &health); err != nil {
		serverError(w, err)
		return
	}
	if health.Status != "ok" {
		fail(w, 503, "MODEL_NOT_READY", "Модель загружается.")
		return
	}
	jsonReply(w, 200, map[string]string{"status": "ready", "corpus_version": info.Version})
}

func (s *server) adminDocuments(w http.ResponseWriter, r *http.Request, _ account, _ uuid.UUID) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Minute)
	defer cancel()
	var input io.Reader
	if r.Method == http.MethodPost {
		if _, err := r.MultipartReader(); err != nil {
			fail(w, 400, "INVALID_FILE", "Ожидается форма с Markdown-файлом.")
			return
		}
		data, err := io.ReadAll(http.MaxBytesReader(w, r.Body, 600<<10))
		if err != nil {
			fail(w, 413, "FILE_TOO_LARGE", "Размер Markdown-файла ограничен 512 КиБ.")
			return
		}
		input = bytes.NewReader(data)
	}
	resp, err := s.external(ctx, r.Method, s.searchURL+"/v1/admin/documents", r.Header.Get("Content-Type"), input)
	if err != nil {
		serverError(w, err)
		return
	}
	defer resp.Body.Close()
	switch resp.StatusCode {
	case 200, 201, 400, 409, 413, 422:
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.WriteHeader(resp.StatusCode)
		_, _ = io.Copy(w, io.LimitReader(resp.Body, 8<<20))
	default:
		serverError(w, fmt.Errorf("corpus administration returned HTTP %d", resp.StatusCode))
	}
}
