package config

import (
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

type Config struct {
	Environment            string
	RedisHost              string
	RedisPort              int
	RedisPassword          string
	RedisSSL               bool
	RedisPrefix            string
	DatabaseURL            string
	AdminSecretKey         string
	JWTSecret              string
	CORSAllowOrigins       []string
}

var GlobalConfig Config

func LoadConfig() {
	_ = godotenv.Load()

	GlobalConfig = Config{
		Environment:      getEnv("ENVIRONMENT", "development"),
		RedisHost:        getEnv("REDIS_HOST", "localhost"),
		RedisPort:        getEnvInt("REDIS_PORT", 6379),
		RedisPassword:    getEnv("REDIS_PASSWORD", ""),
		RedisSSL:         getEnvBool("REDIS_SSL", false),
		RedisPrefix:      getEnv("REDIS_PREFIX", "vp:dev"),
		DatabaseURL:      getEnv("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/vector_pulse?sslmode=disable"),
		AdminSecretKey:   getEnv("ADMIN_SECRET_KEY", "local-dev-admin-key"),
		JWTSecret:        getEnv("JWT_SECRET", "vantix-dev-secret-keep-it-safe"),
		CORSAllowOrigins: strings.Split(getEnv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"), ","),
	}
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if value, ok := os.LookupEnv(key); ok {
		if i, err := strconv.Atoi(value); err == nil {
			return i
		}
	}
	return fallback
}

func getEnvBool(key string, fallback bool) bool {
	if value, ok := os.LookupEnv(key); ok {
		return strings.ToLower(value) == "true" || value == "1"
	}
	return fallback
}
