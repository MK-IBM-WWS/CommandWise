package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/cookiejar"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

func TestIntegration(t *testing.T) {
	dsn := os.Getenv("COMMANDWISE_TEST_DSN")
	if dsn == "" {
		t.Skip("set COMMANDWISE_TEST_DSN to an empty PostgreSQL database")
	}
	ctx, cancel := context.WithCancel(context.Background())
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer pool.Close()
	if err := migrate(ctx, pool.Config()); err != nil {
		t.Fatal(err)
	}

	started := make(chan string, 10)
	gates := map[string]chan struct{}{"first": make(chan struct{}), "second": make(chan struct{}), "third": make(chan struct{})}
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/health":
			jsonReply(w, 200, map[string]string{"status": "ok"})
		case "/v1/corpus":
			fmt.Fprint(w, `{"corpus_version":"test1","distributions":[{"id":"debian","label":"Debian"},{"id":"fedora","label":"Fedora"},{"id":"arch","label":"Arch Linux"}]}`)
		case "/v1/admin/documents":
			fmt.Fprint(w, `{"corpus_version":"test1","items":[]}`)
		case "/v1/search":
			var input struct {
				Query string `json:"query"`
			}
			_ = json.NewDecoder(r.Body).Decode(&input)
			if input.Query == "missing" {
				fmt.Fprint(w, `{"corpus_version":"test1","items":[]}`)
			} else {
				fmt.Fprint(w, `{"corpus_version":"test1","items":[{"chunk_id":"test-chunk","document_id":"find","title":"find","source_url":"https://example.org/find","distribution":"common","text":"## Примеры","section":"Примеры","command":"find","package_version":"1"}]}`)
			}
		case "/apply-template":
			fmt.Fprint(w, `{"prompt":"test prompt"}`)
		case "/tokenize":
			fmt.Fprint(w, `{"tokens":[1,2,3]}`)
		case "/v1/chat/completions":
			var input struct {
				Messages []turn `json:"messages"`
			}
			_ = json.NewDecoder(r.Body).Decode(&input)
			question := input.Messages[len(input.Messages)-1].Content
			w.Header().Set("Content-Type", "text/event-stream")
			fmt.Fprint(w, "data: {\"choices\":[{\"delta\":{\"content\":\"Часть\"}}]}\n\n")
			w.(http.Flusher).Flush()
			started <- question
			if gate := gates[question]; gate != nil {
				select {
				case <-gate:
				case <-r.Context().Done():
					return
				}
			}
			fmt.Fprint(w, "data: {\"choices\":[{\"delta\":{\"content\":\" ответа\"},\"finish_reason\":\"stop\"}]}\n\ndata: [DONE]\n\n")
		default:
			w.WriteHeader(404)
		}
	}))
	defer upstream.Close()
	s := &server{db: pool, http: upstream.Client(), searchURL: upstream.URL, llmURL: upstream.URL, model: "test",
		signingKey: []byte(strings.Repeat("a", 40)), wake: make(chan struct{}, 1),
		authSlots: make(chan struct{}, 4), authAttempts: make(map[string]attempts)}
	defer func() { cancel(); s.workers.Wait() }()
	s.workers.Add(1)
	go s.dispatch(ctx)
	mux := http.NewServeMux()
	s.routes(mux)
	app := httptest.NewServer(s.headers(mux))
	defer app.Close()

	owner := newTestClient(t, app.URL)
	other := newTestClient(t, app.URL)
	admin := newTestClient(t, app.URL)
	testName := func() string { return "t-" + uuid.NewString() }
	userCreds := credentials{testName(), "Test-password"}
	otherCreds := credentials{testName(), "Test-password"}
	adminCreds := credentials{testName(), "Test-password"}
	if err := createAdmin(ctx, pool, adminCreds.Login, adminCreds.Password); err != nil {
		t.Fatal(err)
	}
	owner.json("POST", "/auth/register", userCreds, 201, nil)
	other.json("POST", "/auth/register", otherCreds, 201, nil)
	admin.json("POST", "/auth/login", adminCreds, 200, nil)
	owner.json("GET", "/admin/documents", nil, 403, nil)
	admin.json("GET", "/admin/documents", nil, 200, nil)
	admin.json("GET", "/chats", nil, 403, nil)
	newTestClient(t, app.URL).json("GET", "/chats", nil, 401, nil)

	var distroChat chat
	other.json("POST", "/chats", map[string]string{"distribution": "fedora", "release": "legacy"}, 201, &distroChat)
	if distroChat.Distribution != "fedora" {
		t.Fatalf("expected Fedora chat, got %q", distroChat.Distribution)
	}
	other.json("POST", "/chats", target{"arch"}, 201, &distroChat)
	if distroChat.Distribution != "arch" {
		t.Fatalf("expected Arch chat, got %q", distroChat.Distribution)
	}
	other.json("POST", "/chats", target{"ubuntu"}, 422, nil)

	chats := createTestChats(t, owner, 10)
	owner.json("POST", "/chats", target{"debian"}, 409, nil)
	x := createTestChats(t, other, 1)[0]
	base := func(id uuid.UUID) string { return "/chats/" + id.String() + "/messages" }
	other.json("GET", base(chats[0]), nil, 404, nil)

	first := question{Content: "first", RequestID: uuid.New()}
	var a, b, c message
	owner.json("POST", base(chats[0]), first, 202, &a)
	wantStarted(t, started, "first")
	owner.json("POST", base(chats[0]), first, 409, nil)
	owner.json("POST", base(chats[1]), question{Content: "second", RequestID: uuid.New()}, 202, &b)
	other.json("POST", base(x), question{Content: "third", RequestID: uuid.New()}, 202, &c)
	wantStarted(t, started, "third")
	wantStatus(t, owner, base(chats[1]), b.ID, "queued")
	owner.json("DELETE", "/chats/"+chats[0].String(), nil, 409, nil)
	other.json("POST", base(chats[0])+"/"+a.ID.String()+"/cancel", nil, 404, nil)
	owner.json("POST", base(chats[0])+"/"+a.ID.String()+"/cancel", nil, 204, nil)
	answer := wantStatus(t, owner, base(chats[0]), a.ID, "cancelled")
	if answer.Content != "Часть" {
		t.Fatalf("partial response was not saved: %q", answer.Content)
	}
	wantStarted(t, started, "second")
	close(gates["second"])
	close(gates["third"])
	wantStatus(t, owner, base(chats[1]), b.ID, "complete")
	wantStatus(t, other, base(x), c.ID, "complete")
	var snapshot source
	owner.json("GET", base(chats[0])+"/"+a.ID.String()+"/sources/test-chunk", nil, 200, &snapshot)
	if snapshot.Text != "## Примеры" {
		t.Fatalf("invalid snapshot: %+v", snapshot)
	}
	owner.json("DELETE", "/chats/"+chats[0].String(), nil, 204, nil)
	createTestChats(t, owner, 1)

	data := owner.json("POST", base(chats[1]), question{Content: "missing", Stream: true, RequestID: uuid.New()}, 200, nil)
	for _, fragment := range []string{"event: status", "event: sources", "event: token", "event: done", "no_context"} {
		if !strings.Contains(data, fragment) {
			t.Fatalf("missing %q in SSE: %s", fragment, data)
		}
	}
	if len(started) != 0 {
		t.Fatal("no_context unexpectedly called the LLM")
	}

	bearer := newTestClient(t, app.URL)
	var login authResult
	bearer.header.Set("X-Auth-Mode", "bearer")
	bearer.json("POST", "/auth/login", otherCreds, 200, &login)
	if login.Token == "" {
		t.Fatal("missing JWT")
	}
	bearer.header.Set("Authorization", "Bearer "+login.Token)
	bearer.json("GET", "/auth/me", nil, 200, nil)
	bearer.header.Set("Origin", "https://example.org")
	bearer.json("POST", "/auth/logout", nil, 403, nil)
	bearer.header.Del("Origin")
	bearer.json("POST", "/auth/logout", nil, 204, nil)
	bearer.json("GET", "/auth/me", nil, 401, nil)
}

type testClient struct {
	t      *testing.T
	http   *http.Client
	url    string
	header http.Header
}

func newTestClient(t *testing.T, url string) *testClient {
	jar, err := cookiejar.New(nil)
	if err != nil {
		t.Fatal(err)
	}
	return &testClient{t, &http.Client{Jar: jar, Timeout: 12 * time.Second}, url + "/api/v1", make(http.Header)}
}

func (c *testClient) call(method, path string, input any) (int, []byte, error) {
	b, err := json.Marshal(input)
	if err != nil {
		return 0, nil, err
	}
	req, err := http.NewRequest(method, c.url+path, bytes.NewReader(b))
	if err != nil {
		return 0, nil, err
	}
	req.Header = c.header.Clone()
	req.Header.Set("Content-Type", "application/json")
	res, err := c.http.Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer res.Body.Close()
	payload, err := io.ReadAll(res.Body)
	return res.StatusCode, payload, err
}

func (c *testClient) json(method, path string, input any, expected int, output any) string {
	c.t.Helper()
	status, b, err := c.call(method, path, input)
	if err != nil || status != expected {
		c.t.Fatalf("%s %s: got %d %s (%v), expected %d", method, path, status, b, err, expected)
	}
	if output != nil {
		if err := json.Unmarshal(b, output); err != nil {
			c.t.Fatal(err)
		}
	}
	return string(b)
}

func createTestChats(t *testing.T, c *testClient, n int) []uuid.UUID {
	t.Helper()
	var wg sync.WaitGroup
	ids := make([]uuid.UUID, n)
	failures := make(chan error, n)
	for i := range ids {
		wg.Add(1)
		go func() {
			defer wg.Done()
			status, body, err := c.call("POST", "/chats", target{"debian"})
			if err != nil || status != 201 {
				failures <- fmt.Errorf("create chat: %d %s %v", status, body, err)
				return
			}
			var item chat
			if err := json.Unmarshal(body, &item); err != nil {
				failures <- err
				return
			}
			ids[i] = item.ID
		}()
	}
	wg.Wait()
	close(failures)
	for err := range failures {
		t.Error(err)
	}
	if t.Failed() {
		t.FailNow()
	}
	return ids
}

func wantStarted(t *testing.T, ch <-chan string, expected string) {
	t.Helper()
	select {
	case actual := <-ch:
		if actual != expected {
			t.Fatalf("expected job %q, got %q", expected, actual)
		}
	case <-time.After(8 * time.Second):
		t.Fatalf("job %q was not started", expected)
	}
}

func wantStatus(t *testing.T, c *testClient, path string, id uuid.UUID, status string) message {
	t.Helper()
	for i := 0; i < 75; i++ {
		var out struct {
			Items []message `json:"items"`
		}
		c.json("GET", path, nil, 200, &out)
		for _, m := range out.Items {
			if m.ID == id && m.Status == status {
				return m
			}
		}
		time.Sleep(100 * time.Millisecond)
	}
	t.Fatalf("message %s did not become %s", id, status)
	return message{}
}
