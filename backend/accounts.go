package main

import (
	"errors"
	"net/http"
	"slices"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
)

type accountUpdate struct {
	Login       *string `json:"login"`
	NewPassword *string `json:"new_password"`
}

func (s *server) updateProfile(w http.ResponseWriter, r *http.Request, user account, sid uuid.UUID) {
	var input struct {
		accountUpdate
		CurrentPassword string `json:"current_password"`
	}
	if !readJSON(w, r, &input) {
		return
	}
	if !validAdminPassword(input.CurrentPassword) {
		fail(w, 400, "INVALID_CURRENT_PASSWORD", "Укажите текущий пароль.")
		return
	}
	if !s.allowAuth(r) {
		fail(w, 429, "AUTH_LIMIT", "Слишком много попыток. Подождите минуту.")
		return
	}
	s.editAccount(w, r, user.ID, sid, input.accountUpdate, &input.CurrentPassword)
}

func (s *server) updateUser(w http.ResponseWriter, r *http.Request, user account, sid uuid.UUID) {
	id, ok := pathUUID(w, r, "user_id")
	if !ok {
		return
	}
	if id == user.ID {
		fail(w, 409, "USE_PROFILE", "Редактируйте свой аккаунт через профиль.")
		return
	}
	var input accountUpdate
	if readJSON(w, r, &input) {
		s.editAccount(w, r, id, sid, input, nil)
	}
}

func (s *server) editAccount(w http.ResponseWriter, r *http.Request, id, sid uuid.UUID, input accountUpdate, currentPassword *string) {
	if input.Login == nil && input.NewPassword == nil {
		fail(w, 400, "EMPTY_ACCOUNT_UPDATE", "Укажите новый никнейм или пароль.")
		return
	}
	if input.Login != nil {
		login := normalizeLogin(*input.Login)
		if !loginPattern.MatchString(login) {
			fail(w, 400, "INVALID_LOGIN", "Никнейм от 3 до 40 знаков: латиница, цифры, точка, дефис или подчёркивание.")
			return
		}
		input.Login = &login
	}
	if currentPassword != nil || input.NewPassword != nil {
		if !s.takeAuthSlot(w) {
			return
		}
		defer func() { <-s.authSlots }()
	}

	ctx := r.Context()
	tx, err := s.db.Begin(ctx)
	if err != nil {
		serverError(w, err)
		return
	}
	defer tx.Rollback(ctx)
	var role, oldHash string
	err = tx.QueryRow(ctx, "SELECT role,password_hash FROM accounts WHERE id=$1 FOR UPDATE", id).Scan(&role, &oldHash)
	switch {
	case errors.Is(err, pgx.ErrNoRows):
		if currentPassword != nil {
			fail(w, 401, "AUTH_REQUIRED", "Войдите в аккаунт.")
		} else {
			fail(w, 404, "NOT_FOUND", "Аккаунт не найден.")
		}
		return
	case err != nil:
		serverError(w, err)
		return
	}
	if currentPassword != nil && !passwordMatches(oldHash, *currentPassword) {
		fail(w, 403, "BAD_CURRENT_PASSWORD", "Текущий пароль неверен.")
		return
	}

	var passwordHash *string
	if input.NewPassword != nil {
		password := *input.NewPassword
		switch {
		case role == "admin" && !validAdminPassword(password):
			fail(w, 400, "INVALID_PASSWORD", "Укажите непустой пароль администратора до 4096 байт.")
			return
		case role != "admin" && !validPassword(password):
			fail(w, 400, "INVALID_PASSWORD", "Пароль от 8 символов до 72 байт.")
			return
		}
		hash, err := hashPassword(role, password)
		if err != nil {
			serverError(w, err)
			return
		}
		passwordHash = &hash
	}
	var updated account
	err = tx.QueryRow(ctx, `UPDATE accounts SET login=coalesce($2,login),
		password_hash=coalesce($3,password_hash) WHERE id=$1 RETURNING id,login,role`,
		id, input.Login, passwordHash).Scan(&updated.ID, &updated.Login, &updated.Role)
	switch {
	case loginIsTaken(err):
		fail(w, 409, "LOGIN_EXISTS", "Этот никнейм уже занят.")
		return
	case err != nil:
		serverError(w, err)
		return
	}
	if passwordHash != nil {
		// For an admin reset the operator's session belongs to a different account.
		if _, err := tx.Exec(ctx, "DELETE FROM sessions WHERE account_id=$1 AND id<>$2", id, sid); err != nil {
			serverError(w, err)
			return
		}
	}
	if err := tx.Commit(ctx); err != nil {
		serverError(w, err)
		return
	}
	jsonReply(w, 200, updated)
}

func (s *server) listUsers(w http.ResponseWriter, r *http.Request, _ account, _ uuid.UUID) {
	rows, err := s.db.Query(r.Context(), "SELECT id,login,role FROM accounts ORDER BY login")
	if err != nil {
		serverError(w, err)
		return
	}
	items, err := pgx.AppendRows([]account{}, rows, pgx.RowToStructByPos[account])
	if err != nil {
		serverError(w, err)
		return
	}
	jsonReply(w, 200, map[string][]account{"items": items})
}

func (s *server) deleteUser(w http.ResponseWriter, r *http.Request, user account, _ uuid.UUID) {
	id, ok := pathUUID(w, r, "user_id")
	if !ok {
		return
	}
	if id == user.ID {
		fail(w, 409, "SELF_DELETE", "Администратор не может удалить собственный аккаунт.")
		return
	}

	ctx := r.Context()
	tx, err := s.db.Begin(ctx)
	if err != nil {
		serverError(w, err)
		return
	}
	defer tx.Rollback(ctx)
	// Lock both accounts in the same order to prevent concurrent admins from deleting each other.
	rows, err := tx.Query(ctx, "SELECT id FROM accounts WHERE id IN ($1,$2) ORDER BY id FOR UPDATE", id, user.ID)
	if err != nil {
		serverError(w, err)
		return
	}
	accounts, err := pgx.CollectRows(rows, pgx.RowTo[uuid.UUID])
	if err != nil {
		serverError(w, err)
		return
	}
	if !slices.Contains(accounts, user.ID) {
		fail(w, 401, "AUTH_REQUIRED", "Войдите в аккаунт.")
		return
	}
	if !slices.Contains(accounts, id) {
		fail(w, 404, "NOT_FOUND", "Аккаунт не найден.")
		return
	}
	if _, err := tx.Exec(ctx, "DELETE FROM accounts WHERE id=$1", id); err != nil {
		serverError(w, err)
		return
	}
	if err := tx.Commit(ctx); err != nil {
		serverError(w, err)
		return
	}
	w.WriteHeader(204)
}
