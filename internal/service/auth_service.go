package service

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
	"vector-pulse/internal/config"
	"vector-pulse/internal/repository"

	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/crypto/bcrypt"
)

type AuthService struct {
	repo repository.ReadWriter
}

type AuthResult struct {
	Message string
	Email   string
	TeamID  string
	Role    string
	Token   string
}

func NewAuthService(repo repository.ReadWriter) *AuthService {
	return &AuthService{repo: repo}
}

func (s *AuthService) Signup(ctx context.Context, email, password string) (AuthResult, error) {
	email = normalizeEmail(email)
	if email == "" || len(password) < 6 {
		return AuthResult{}, fmt.Errorf("email and password(min 6) are required")
	}

	if _, err := s.repo.GetUserByEmail(ctx, email); err == nil {
		return AuthResult{}, fmt.Errorf("email already registered")
	} else if !errors.Is(err, sql.ErrNoRows) {
		return AuthResult{}, err
	}

	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return AuthResult{}, err
	}

	teamID := buildTeamID(email)
	if err := s.repo.CreateUser(ctx, repository.User{
		Email:        email,
		PasswordHash: string(hash),
		TeamID:       teamID,
		Role:         "ADMIN",
	}); err != nil {
		return AuthResult{}, err
	}

	token, err := issueToken(email, teamID, "ADMIN")
	if err != nil {
		return AuthResult{}, err
	}

	return AuthResult{
		Message: "Account created successfully",
		Email:   email,
		TeamID:  teamID,
		Role:    "ADMIN",
		Token:   token,
	}, nil
}

func (s *AuthService) Login(ctx context.Context, email, password string) (AuthResult, error) {
	email = normalizeEmail(email)
	if email == "" || password == "" {
		return AuthResult{}, fmt.Errorf("email and password are required")
	}

	user, err := s.repo.GetUserByEmail(ctx, email)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return AuthResult{}, fmt.Errorf("invalid credentials")
		}
		return AuthResult{}, err
	}

	if bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)) != nil {
		return AuthResult{}, fmt.Errorf("invalid credentials")
	}

	token, err := issueToken(user.Email, user.TeamID, user.Role)
	if err != nil {
		return AuthResult{}, err
	}

	return AuthResult{
		Message: "Logged in successfully",
		Email:   user.Email,
		TeamID:  user.TeamID,
		Role:    user.Role,
		Token:   token,
	}, nil
}

func normalizeEmail(email string) string {
	return strings.TrimSpace(strings.ToLower(email))
}

func buildTeamID(email string) string {
	name := strings.Split(email, "@")[0]
	name = strings.ReplaceAll(name, ".", "_")
	return "team_" + name
}

func issueToken(email, teamID, role string) (string, error) {
	claims := jwt.MapClaims{
		"email":   email,
		"team_id": teamID,
		"role":    role,
		"exp":     time.Now().Add(7 * 24 * time.Hour).Unix(),
		"iat":     time.Now().Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(config.GlobalConfig.JWTSecret))
}
