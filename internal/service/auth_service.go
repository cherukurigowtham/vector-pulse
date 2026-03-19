package service

import (
	"context"
	"errors"
	"vector-pulse/internal/core"
	"vector-pulse/internal/domain"
	"vector-pulse/internal/repository"
)

type AuthService struct {
	pgStore    repository.Store
	redisStore repository.Cache
}

func NewAuthService(pgStore repository.Store, redisStore repository.Cache) *AuthService {
	return &AuthService{
		pgStore:    pgStore,
		redisStore: redisStore,
	}
}

func (s *AuthService) Signup(ctx context.Context, req domain.AuthRequest) (string, string, error) {
	exists, err := s.redisStore.HExists(ctx, "user:"+req.Email, "pwd_hash")
	if err != nil {
		return "", "", err
	}
	if exists {
		return "", "", errors.New("email already registered")
	}

	salt, err := core.GenerateSalt()
	if err != nil {
		return "", "", err
	}
	pwdHash := core.HashPassword(req.Password, salt)
	
	rawKey, err := core.GenerateSecureKey()
	if err != nil {
		return "", "", err
	}
	legacyHash := core.HashKey(rawKey)
	teamID, _ := core.GenerateSalt()
	teamID = teamID[:8]

	err = s.pgStore.CreateTeam(ctx, teamID, req.Email+"'s Team", req.Email)
	if err != nil {
		return "", "", err
	}

	err = s.redisStore.HSet(ctx, "user:"+req.Email, map[string]interface{}{
		"pwd_hash": pwdHash,
		"salt":     salt,
		"key_hash": legacyHash,
		"plan":     "free",
		"role":     "ADMIN",
		"team_id":  teamID,
	})
	if err != nil {
		return "", "", err
	}
	
	s.redisStore.Set(ctx, "emailkey:"+req.Email, legacyHash, 0)

	token, err := core.CreateJWTToken(req.Email, "ADMIN", teamID)
	return token, rawKey, err
}

func (s *AuthService) Login(ctx context.Context, req domain.AuthRequest) (string, error) {
	userData, err := s.redisStore.HGetAll(ctx, "user:"+req.Email)
	if err != nil {
		return "", err
	}
	if len(userData) == 0 {
		return "", errors.New("invalid credentials")
	}

	salt, ok := userData["salt"]
	if !ok {
		return "", errors.New("invalid credentials")
	}

	var expectedHash string
	if hash, exists := userData["pwd_hash"]; exists {
		expectedHash = hash
	} else if hash, exists := userData["password_hash"]; exists {
		expectedHash = hash
	}

	providedHash := core.HashPassword(req.Password, salt)
	if providedHash != expectedHash {
		return "", errors.New("invalid credentials")
	}

	role := userData["role"]
	if role == "" {
		role = "VIEWER"
	}
	teamID := userData["team_id"]
	if teamID == "" {
		teamID = "personal"
	}

	token, err := core.CreateJWTToken(req.Email, role, teamID)
	return token, err
}

func (s *AuthService) GetUser(ctx context.Context, email string) (*domain.User, error) {
	userData, err := s.redisStore.HGetAll(ctx, "user:"+email)
	if err != nil {
		return nil, err
	}
	if len(userData) == 0 {
		return nil, errors.New("user not found")
	}

	return &domain.User{
		Email:  email,
		Role:   userData["role"],
		TeamID: userData["team_id"],
	}, nil
}
