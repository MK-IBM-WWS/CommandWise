package main

import (
	"context"
	"errors"
	"net"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"golang.org/x/crypto/bcrypt"
)

const (
	cookieName      = "cw_session"
	sessionDuration = 24 * time.Hour
	tokenIssuer     = "commandwise"
)

var loginPattern = regexp.MustCompile(`^[a-z0-9_.-]{3,40}$`)
var dummyHash, _ = bcrypt.GenerateFromPassword([]byte("no-account-sample"), bcrypt.DefaultCost)

type account struct {
	ID    uuid.UUID `json:"id"`
	Login string    `json:"login"`
	Role  string    `json:"role"`
}

type credentials struct {
	Login    string `json:"login"`
	Password string `json:"password"`
}

type authResult struct {
	User  account `json:"user"`
	Token string  `json:"token,omitempty"`
}

type attempts struct {
	count int
	until time.Time
}

func validCredentials(c credentials) bool {
	return loginPattern.MatchString(c.Login) && validPassword(c.Password)
}

func validPassword(password string) bool {
	return utf8.RuneCountInString(password) >= 8 && len(password) <= 72 && !strings.ContainsRune(password, 0)
}

func normalizeLogin(login string) string { return strings.ToLower(strings.TrimSpace(login)) }

func loginIsTaken(err error) bool {
	var pgErr *pgconn.PgError
	return errors.As(err, &pgErr) && pgErr.Code == "23505"
}

func createAdmin(ctx context.Context, db *pgxpool.Pool, login, password string) error {
	c := credentials{normalizeLogin(login), password}
	if !loginPattern.MatchString(c.Login) {
		return errors.New("логин администратора от 3 до 40 знаков: латиница, цифры, точка, дефис или подчёркивание")
	}
	if !validAdminPassword(c.Password) {
		return errors.New("укажите непустой пароль администратора до 4096 байт")
	}
	hash, err := hashPassword("admin", c.Password)
	if err != nil {
		return err
	}
	command, err := db.Exec(ctx, `INSERT INTO accounts (id,login,password_hash,role)
		VALUES ($1,$2,$3,'admin') ON CONFLICT (login) DO NOTHING`, uuid.New(), c.Login, hash)
	if err != nil {
		return err
	}
	if command.RowsAffected() == 1 {
		return nil
	}
	var role, stored string
	if err := db.QueryRow(ctx, "SELECT role,password_hash FROM accounts WHERE login=$1", c.Login).Scan(&role, &stored); err != nil {
		return err
	}
	if role != "admin" || !passwordMatches(stored, c.Password) {
		return errors.New("the login already exists with different credentials")
	}
	return nil
}

func (s *server) allowAuth(r *http.Request) bool {
	ip := r.Header.Get("X-Real-IP")
	if net.ParseIP(ip) == nil {
		ip, _, _ = net.SplitHostPort(r.RemoteAddr)
	}
	now := time.Now()
	s.authMu.Lock()
	defer s.authMu.Unlock()
	if len(s.authAttempts) >= 1024 {
		for key, entry := range s.authAttempts {
			if !now.Before(entry.until) {
				delete(s.authAttempts, key)
			}
		}
	}
	entry, exists := s.authAttempts[ip]
	if !exists && len(s.authAttempts) >= 1024 {
		return false
	}
	if !now.Before(entry.until) {
		entry = attempts{until: now.Add(time.Minute)}
	}
	if entry.count >= 20 {
		return false
	}
	entry.count++
	s.authAttempts[ip] = entry
	return true
}

func (s *server) entry(register bool) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !s.allowAuth(r) {
			fail(w, 429, "AUTH_LIMIT", "Слишком много попыток. Подождите минуту.")
			return
		}
		if !s.takeAuthSlot(w) {
			return
		}
		defer func() { <-s.authSlots }()
		var c credentials
		if !readJSON(w, r, &c) {
			return
		}
		c.Login = normalizeLogin(c.Login)
		if register {
			if !validCredentials(c) {
				fail(w, 400, "INVALID_CREDENTIALS", "Логин от 3 до 40 знаков: латиница, цифры, точка, дефис или подчёркивание. Пароль от 8 символов до 72 байт.")
				return
			}
			s.register(w, r, c)
			return
		}
		if !loginPattern.MatchString(c.Login) || !validAdminPassword(c.Password) {
			fail(w, 400, "INVALID_CREDENTIALS", "Проверьте формат логина и заполните пароль.")
			return
		}
		var user account
		var hash string
		err := s.db.QueryRow(r.Context(), "SELECT id,login,password_hash,role FROM accounts WHERE login=$1", c.Login).
			Scan(&user.ID, &user.Login, &hash, &user.Role)
		if errors.Is(err, pgx.ErrNoRows) {
			hash = string(dummyHash)
		} else if err != nil {
			serverError(w, err)
			return
		}
		if !passwordMatches(hash, c.Password) || err != nil {
			fail(w, 401, "BAD_LOGIN", "Неверный логин или пароль.")
			return
		}
		s.issue(w, r, user, hash, 200)
	}
}

func (s *server) takeAuthSlot(w http.ResponseWriter) bool {
	select {
	case s.authSlots <- struct{}{}:
		return true
	default:
		fail(w, 429, "AUTH_LIMIT", "Слишком много запросов. Повторите попытку.")
		return false
	}
}

func (s *server) register(w http.ResponseWriter, r *http.Request, c credentials) {
	hash, err := hashPassword("user", c.Password)
	if err != nil {
		serverError(w, err)
		return
	}
	user := account{uuid.New(), c.Login, "user"}
	_, err = s.db.Exec(r.Context(), "INSERT INTO accounts (id,login,password_hash,role) VALUES ($1,$2,$3,'user')", user.ID, user.Login, hash)
	if loginIsTaken(err) {
		fail(w, 409, "LOGIN_EXISTS", "Этот логин уже занят.")
		return
	}
	if err != nil {
		serverError(w, err)
		return
	}
	s.issue(w, r, user, hash, 201)
}

func (s *server) issue(w http.ResponseWriter, r *http.Request, user account, hash string, status int) {
	now := time.Now()
	expiry := jwt.NewNumericDate(now.Add(sessionDuration))
	sid := uuid.New()
	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.RegisteredClaims{
		Subject: user.ID.String(), ID: sid.String(), Issuer: tokenIssuer,
		IssuedAt: jwt.NewNumericDate(now), ExpiresAt: expiry,
	}).SignedString(s.signingKey)
	if err != nil {
		serverError(w, err)
		return
	}
	// Serialize issuing a session with credential changes so a verified old password cannot outlive a reset.
	result, err := s.db.Exec(r.Context(), `INSERT INTO sessions (id,account_id,expires_at)
		SELECT $1,id,$2 FROM accounts WHERE id=$3 AND login=$4 AND password_hash=$5 FOR SHARE`,
		sid, expiry.Time, user.ID, user.Login, hash)
	if err != nil {
		serverError(w, err)
		return
	}
	if result.RowsAffected() == 0 {
		fail(w, 401, "BAD_LOGIN", "Неверный логин или пароль.")
		return
	}
	response := authResult{User: user}
	if r.Header.Get("X-Auth-Mode") == "bearer" {
		response.Token = token
	} else {
		s.sessionCookie(w, r, token, int(sessionDuration/time.Second))
	}
	jsonReply(w, status, response)
}

func (s *server) sessionCookie(w http.ResponseWriter, r *http.Request, value string, maxAge int) {
	http.SetCookie(w, &http.Cookie{Name: cookieName, Value: value, Path: "/", HttpOnly: true,
		Secure: s.secureCookie || r.TLS != nil, SameSite: http.SameSiteLaxMode, MaxAge: maxAge})
}

type accountHandler func(http.ResponseWriter, *http.Request, account, uuid.UUID)

func (s *server) protected(role string, handle accountHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var raw string
		if header := r.Header.Get("Authorization"); header != "" {
			scheme, value, _ := strings.Cut(header, " ")
			if strings.EqualFold(scheme, "Bearer") {
				raw = value
			}
		} else if cookie, err := r.Cookie(cookieName); err == nil {
			raw = cookie.Value
		}
		var claims jwt.RegisteredClaims
		_, err := jwt.ParseWithClaims(raw, &claims, func(*jwt.Token) (any, error) { return s.signingKey, nil },
			jwt.WithValidMethods([]string{"HS256"}), jwt.WithIssuer(tokenIssuer), jwt.WithExpirationRequired())
		userID, idErr := uuid.Parse(claims.Subject)
		sid, sidErr := uuid.Parse(claims.ID)
		if err != nil || idErr != nil || sidErr != nil {
			fail(w, 401, "AUTH_REQUIRED", "Войдите в аккаунт.")
			return
		}
		var user account
		err = s.db.QueryRow(r.Context(), `SELECT a.id,a.login,a.role FROM sessions s JOIN accounts a ON a.id=s.account_id
			WHERE s.id=$1 AND a.id=$2 AND s.expires_at > now()`, sid, userID).Scan(&user.ID, &user.Login, &user.Role)
		if errors.Is(err, pgx.ErrNoRows) {
			fail(w, 401, "AUTH_REQUIRED", "Войдите в аккаунт.")
			return
		}
		if err != nil {
			serverError(w, err)
			return
		}
		if role != "" && role != user.Role {
			fail(w, 403, "FORBIDDEN", "Для этого действия нужна другая роль.")
			return
		}
		handle(w, r, user, sid)
	}
}

func (s *server) logout(w http.ResponseWriter, r *http.Request, _ account, sid uuid.UUID) {
	if _, err := s.db.Exec(r.Context(), "DELETE FROM sessions WHERE id=$1", sid); err != nil {
		serverError(w, err)
		return
	}
	s.sessionCookie(w, r, "", -1)
	w.WriteHeader(204)
}

func (s *server) expireSessions(ctx context.Context) {
	defer s.workers.Done()
	ticker := time.NewTicker(time.Hour)
	defer ticker.Stop()
	for {
		_, _ = s.db.Exec(ctx, "DELETE FROM sessions WHERE expires_at <= now()")
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func (s *server) sameOrigin(r *http.Request) bool {
	if r.Method == "GET" || r.Method == "HEAD" || r.Method == "OPTIONS" {
		return true
	}
	raw := r.Header.Get("Origin")
	if raw == "" {
		return r.Header.Get("Sec-Fetch-Site") != "cross-site"
	}
	if s.publicOrigin != "" {
		return raw == s.publicOrigin
	}
	origin, err := url.Parse(raw)
	return err == nil && origin.User == nil && origin.Path == "" && origin.RawQuery == "" && origin.Fragment == "" &&
		strings.EqualFold(origin.Host, r.Host) && (origin.Scheme == "http" || origin.Scheme == "https")
}
