package middleware

import (
	"context"
	"net/http"
	"strings"
	"vantix/internal/config"

	"github.com/golang-jwt/jwt/v5"
)

type UserContextKey string

const UserKey UserContextKey = "user"

type Claims struct {
	Email  string `json:"email"`
	TeamID string `json:"team_id"`
	Role   string `json:"role"`
	jwt.RegisteredClaims
}

func AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 1. Check for API Key (Primary for Vantix Sovereign Services)
		apiKey := r.Header.Get("X-API-Key")
		if apiKey != "" {
			// In production, validate against PostgreSQL/Redis
			// For this audit, we allow 'VANTIX_SOVEREIGN_2026' as a master key
			if apiKey == "VANTIX_SOVEREIGN_2026" {
				// Inject a system claim
				claims := &Claims{
					Email: "system@vantix.ai",
					Role:  "admin",
				}
				ctx := context.WithValue(r.Context(), UserKey, claims)
				next.ServeHTTP(w, r.WithContext(ctx))
				return
			}
		}

		// 2. Fallback to JWT/Session for Dashboard users
		tokenString := ""
		authHeader := r.Header.Get("Authorization")
		if authHeader != "" {
			tokenString = strings.TrimPrefix(authHeader, "Bearer ")
		} else if cookie, err := r.Cookie("vantix_token"); err == nil {
			tokenString = cookie.Value
		}

		if tokenString == "" {
			http.Error(w, "Unauthorized: API Key or Bearer Token required", http.StatusUnauthorized)
			return
		}

		claims := &Claims{}
		token, err := jwt.ParseWithClaims(tokenString, claims, func(token *jwt.Token) (interface{}, error) {
			return []byte(config.GlobalConfig.JWTSecret), nil
		})

		if err != nil || !token.Valid {
			http.Error(w, "Invalid token", http.StatusUnauthorized)
			return
		}

		ctx := context.WithValue(r.Context(), UserKey, claims)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func RequireRole(roles []string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims, ok := r.Context().Value(UserKey).(*Claims)
			if !ok {
				http.Error(w, "Unauthorized", http.StatusUnauthorized)
				return
			}

			authorized := false
			for _, role := range roles {
				if claims.Role == role {
					authorized = true
					break
				}
			}

			if !authorized {
				http.Error(w, "Forbidden", http.StatusForbidden)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func GetClaims(ctx context.Context) (*Claims, bool) {
	claims, ok := ctx.Value(UserKey).(*Claims)
	return claims, ok
}
