package handler

import (
	"encoding/json"
	"log"
	"net/http"
	"time"
	"github.com/golang-jwt/jwt/v5"
	"vector-pulse/internal/core"
	"vector-pulse/internal/domain"
	"vector-pulse/internal/service"
)

type AuthHandler struct {
	authService *service.AuthService
}

func NewAuthHandler(authService *service.AuthService) *AuthHandler {
	return &AuthHandler{authService: authService}
}

func (h *AuthHandler) Signup(w http.ResponseWriter, r *http.Request) {
	log.Printf("Received signup request from %s", r.RemoteAddr)
	var req domain.AuthRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("Error decoding signup request: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	log.Printf("Processing signup for email: %s", req.Email)

	token, apiKey, err := h.authService.Signup(r.Context(), req)
	if err != nil {
		log.Printf("Signup service error: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	http.SetCookie(w, &http.Cookie{
		Name:     "vp_token",
		Value:    token,
		Path:     "/",
		HttpOnly: true,
		Expires:  time.Now().Add(24 * time.Hour),
		SameSite: http.SameSiteNoneMode,
		Secure:   true,
	})

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(domain.AuthResponse{Message: "Account created successfully", APIKey: apiKey})
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	log.Printf("Received login request for %s", r.RemoteAddr)
	var req domain.AuthRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("Error decoding login request: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	log.Printf("Processing login for email: %s", req.Email)

	token, err := h.authService.Login(r.Context(), req)
	if err != nil {
		log.Printf("Login service error for %s: %v", req.Email, err)
		http.Error(w, "Invalid credentials", http.StatusUnauthorized)
		return
	}

	http.SetCookie(w, &http.Cookie{
		Name:     "vp_token",
		Value:    token,
		Path:     "/",
		HttpOnly: true,
		Expires:  time.Now().Add(24 * time.Hour),
		SameSite: http.SameSiteNoneMode,
		Secure:   true,
	})

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(domain.AuthResponse{Status: "success", Message: "Logged in successfully"})
}

func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	http.SetCookie(w, &http.Cookie{
		Name:     "vp_token",
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		Expires:  time.Unix(0, 0),
		SameSite: http.SameSiteNoneMode,
		Secure:   true,
	})
	w.WriteHeader(http.StatusOK)
}

func (h *AuthHandler) Me(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie("vp_token")
	if err != nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	token, err := jwt.Parse(cookie.Value, func(token *jwt.Token) (interface{}, error) {
		return core.GetJWTSecret(), nil
	})

	if err != nil || !token.Valid {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	email := claims["sub"].(string)
	user, err := h.authService.GetUser(r.Context(), email)
	if err != nil {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	// email := claims["sub"].(string) - already used above

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"email":    user.Email,
		"role":     user.Role,
		"team_id":  user.TeamID,
		"is_admin": user.Role == "ADMIN",
		"api_key":  "vp_live_********************", // Placeholder for masking
	})
}
