package main

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"strings"

	"golang.org/x/crypto/argon2"
	"golang.org/x/crypto/bcrypt"
)

const (
	adminPasswordMax   = 4096
	adminHashVersion   = "cw-argon2id-v1$"
	adminHashTime      = 2
	adminHashMemory    = 32 * 1024 // KiB
	adminHashThreads   = 1
	adminHashSaltSize  = 16
	adminHashValueSize = 32
)

func validAdminPassword(password string) bool {
	return password != "" && len(password) <= adminPasswordMax && !strings.ContainsRune(password, 0)
}

func hashPassword(role, password string) (string, error) {
	if role != "admin" {
		hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
		return string(hash), err
	}
	salt := make([]byte, adminHashSaltSize, adminHashSaltSize+adminHashValueSize)
	rand.Read(salt)
	key := argon2.IDKey([]byte(password), salt, adminHashTime, adminHashMemory, adminHashThreads, adminHashValueSize)
	return adminHashVersion + base64.RawStdEncoding.EncodeToString(append(salt, key...)), nil
}

func passwordMatches(hash, password string) bool {
	encoded, isArgon := strings.CutPrefix(hash, adminHashVersion)
	if !isArgon {
		return len(password) <= 72 && bcrypt.CompareHashAndPassword([]byte(hash), []byte(password)) == nil
	}
	data, err := base64.RawStdEncoding.DecodeString(encoded)
	if err != nil || len(data) != adminHashSaltSize+adminHashValueSize {
		return false
	}
	salt, expected := data[:adminHashSaltSize], data[adminHashSaltSize:]
	actual := argon2.IDKey([]byte(password), salt, adminHashTime, adminHashMemory, adminHashThreads, adminHashValueSize)
	return subtle.ConstantTimeCompare(actual, expected) == 1
}
