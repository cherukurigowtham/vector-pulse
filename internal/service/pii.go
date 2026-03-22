package service

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
)

type PIIService struct {
	salt string
}

func NewPIIService() *PIIService {
	salt := os.Getenv("PII_SALT")
	if salt == "" {
		salt = "vector-pulse-collective-defense-2024" // Match Python parity
	}
	return &PIIService{salt: salt}
}

// Tokenize hashes a sensitive string with the global salt
func (s *PIIService) Tokenize(input string) string {
	if input == "" {
		return ""
	}
	h := sha256.New()
	h.Write([]byte(input + s.salt))
	return hex.EncodeToString(h.Sum(nil))
}

// Identify returns a truncated version of the token for logging (first 8 chars)
func (s *PIIService) Identify(input string) string {
	token := s.Tokenize(input)
	if len(token) > 8 {
		return token[:8]
	}
	return token
}
