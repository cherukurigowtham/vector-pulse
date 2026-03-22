package core

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"time"
	"os"

	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/pbkdf2"
)

func GetJWTSecret() []byte {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		secret = "vantix-dev-secret-keep-it-safe"
	}
	return []byte(secret)
}

func GenerateSalt() (string, error) {
	b := make([]byte, 16)
	_, err := rand.Read(b)
	if err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

func HashPassword(password, salt string) string {
	key := pbkdf2.Key([]byte(password), []byte(salt), 100000, 32, sha256.New)
	return hex.EncodeToString(key)
}

func GenerateSecureKey() (string, error) {
	b := make([]byte, 32)
	_, err := rand.Read(b)
	if err != nil {
		return "", err
	}
	return "vp_live_" + hex.EncodeToString(b), nil
}

func HashKey(key string) string {
	h := sha256.New()
	h.Write([]byte(key))
	return hex.EncodeToString(h.Sum(nil))
}

func CreateJWTToken(email, role, teamID string) (string, error) {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":     email,
		"role":    role,
		"team_id": teamID,
		"exp":     time.Now().Add(time.Hour * 24).Unix(),
	})
	return token.SignedString(GetJWTSecret())
}
