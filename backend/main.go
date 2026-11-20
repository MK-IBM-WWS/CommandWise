package main

import (
	"context"
	"embed"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/jackc/pgx/v5/stdlib"
	"github.com/pressly/goose/v3"
)

//go:embed migrations/*.sql
var migrations embed.FS

type server struct {
	db                                              *pgxpool.Pool
	http                                            *http.Client
	searchURL, llmURL, model, address, publicOrigin string
	signingKey                                      []byte
	secureCookie                                    bool
	wake                                            chan struct{}
	workers                                         sync.WaitGroup
	authSlots                                       chan struct{}
	authMu                                          sync.Mutex
	authAttempts                                    map[string]attempts
}

func env(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	if err := run(ctx); err != nil {
		log.Fatal(err)
	}
}

func run(ctx context.Context) error {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		return errors.New("DATABASE_URL is required")
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return err
	}
	defer pool.Close()
	if err := pool.Ping(ctx); err != nil {
		return err
	}

	// Keep only one scheduler active across restarts or accidental extra replicas.
	if len(os.Args) == 1 {
		lease, err := pool.Acquire(ctx)
		if err != nil {
			return err
		}
		defer lease.Release()
		var leader bool
		if err := lease.QueryRow(ctx, "SELECT pg_try_advisory_lock(780321)").Scan(&leader); err != nil {
			return err
		}
		if !leader {
			return errors.New("another CommandWise backend is running")
		}
		defer lease.Exec(context.Background(), "SELECT pg_advisory_unlock(780321)")
	}
	if err := migrate(ctx, pool.Config()); err != nil {
		return err
	}
	if len(os.Args) > 1 {
		if len(os.Args) != 3 || os.Args[1] != "admin" {
			return errors.New("usage: commandwise [admin LOGIN]")
		}
		input, err := io.ReadAll(io.LimitReader(os.Stdin, 75))
		if err != nil {
			return err
		}
		return createAdmin(ctx, pool, os.Args[2], strings.TrimSuffix(string(input), "\n"))
	}

	s := &server{
		db:           pool,
		http:         &http.Client{},
		searchURL:    strings.TrimRight(env("SEARCH_URL", "http://127.0.0.1:8000"), "/"),
		llmURL:       strings.TrimRight(env("LLM_URL", "http://127.0.0.1:8082"), "/"),
		model:        env("LLM_MODEL", "qwen3.5-4b"),
		address:      env("LISTEN_ADDR", ":8081"),
		publicOrigin: strings.TrimRight(os.Getenv("PUBLIC_ORIGIN"), "/"),
		secureCookie: os.Getenv("COOKIE_SECURE") == "true",
		signingKey:   []byte(os.Getenv("JWT_SECRET")),
		wake:         make(chan struct{}, 1),
		authSlots:    make(chan struct{}, 4),
		authAttempts: make(map[string]attempts),
	}
	if len(s.signingKey) < 32 {
		return errors.New("JWT_SECRET needs at least 32 bytes")
	}
	if s.publicOrigin != "" {
		origin, err := url.Parse(s.publicOrigin)
		if err != nil || origin.Host == "" || origin.User != nil || origin.Path != "" || origin.RawQuery != "" || origin.Fragment != "" || (origin.Scheme != "https" && origin.Scheme != "http") {
			return errors.New("PUBLIC_ORIGIN must be an HTTP(S) origin, e.g. https://chat.example.org")
		}
		if origin.Scheme == "https" {
			s.secureCookie = true
		}
	}
	if _, err := pool.Exec(ctx, `UPDATE messages SET status = CASE WHEN cancel_requested THEN 'cancelled' ELSE 'error' END,
		finish_reason = CASE WHEN cancel_requested THEN 'cancelled' ELSE '' END,
		error = CASE WHEN cancel_requested THEN '' ELSE 'Генерация прервана перезапуском сервера.' END
		WHERE status='generating'`); err != nil {
		return err
	}

	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	mux := http.NewServeMux()
	s.routes(mux)
	web := &http.Server{Addr: s.address, Handler: s.headers(mux), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 32 << 10}
	result := make(chan error, 1)
	go func() { result <- web.ListenAndServe() }()
	log.Printf("CommandWise API listening on %s", s.address)
	s.workers.Add(2)
	go s.dispatch(ctx)
	go s.expireSessions(ctx)
	select {
	case err = <-result:
		cancel()
	case <-ctx.Done():
		shutdown, stop := context.WithTimeout(context.Background(), 8*time.Second)
		defer stop()
		err = web.Shutdown(shutdown)
		if err != nil {
			_ = web.Close()
		}
	}
	s.workers.Wait()
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}

func migrate(ctx context.Context, config *pgxpool.Config) error {
	sql := stdlib.OpenDB(*config.ConnConfig)
	defer sql.Close()
	goose.SetBaseFS(migrations)
	if err := goose.SetDialect("postgres"); err != nil {
		return err
	}
	if err := goose.UpContext(ctx, sql, "migrations"); err != nil {
		return fmt.Errorf("migrations: %w", err)
	}
	return nil
}
