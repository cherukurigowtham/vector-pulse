package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"time"
	"vector-pulse/internal/middleware"
	"vector-pulse/internal/service"
)

type AuthHandler struct {
	authService *service.AuthService
}

type authRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

func NewAuthHandler(authService *service.AuthService) *AuthHandler {
	return &AuthHandler{authService: authService}
}

func (h *AuthHandler) Signup(w http.ResponseWriter, r *http.Request) {
	var req authRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	result, err := h.authService.Signup(ctx, req.Email, req.Password)
	if err != nil {
		status := http.StatusInternalServerError
		if strings.Contains(err.Error(), "required") || strings.Contains(err.Error(), "registered") {
			status = http.StatusBadRequest
		}
		http.Error(w, err.Error(), status)
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"message":  result.Message,
		"email":    result.Email,
		"team_id":  result.TeamID,
		"is_admin": strings.EqualFold(result.Role, "ADMIN"),
		"token":    result.Token,
	})
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var req authRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	result, err := h.authService.Login(ctx, req.Email, req.Password)
	if err != nil {
		status := http.StatusInternalServerError
		if strings.Contains(err.Error(), "invalid credentials") {
			status = http.StatusUnauthorized
		} else if strings.Contains(err.Error(), "required") {
			status = http.StatusBadRequest
		}
		http.Error(w, err.Error(), status)
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"message":  result.Message,
		"email":    result.Email,
		"team_id":  result.TeamID,
		"is_admin": strings.EqualFold(result.Role, "ADMIN"),
		"token":    result.Token,
	})
}

func (h *AuthHandler) Me(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaims(r.Context())
	if !ok {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"email":    claims.Email,
		"team_id":  claims.TeamID,
		"is_admin": strings.EqualFold(claims.Role, "ADMIN"),
	})
}

func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status":  "success",
		"message": "Logged out successfully",
	})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
