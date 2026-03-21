package middleware

import (
	"context"
	"net/http"
	"strings"
	"vector-pulse/internal/config"

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
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			// API Key fallback?
			if r.Header.Get("x-api-key") != "" {
				// Mock API key validation
				next.ServeHTTP(w, r)
				return
			}
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		tokenString := strings.TrimPrefix(authHeader, "Bearer ")
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
