package repository

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"vector-pulse/internal/domain"
)

type Store interface {
	CreateTeam(ctx context.Context, teamID, name, ownerEmail string) error
	GetUserRoleAndTeam(ctx context.Context, email string) (*domain.User, error)
}

type PostgresStore struct {
	db *pgxpool.Pool
}

func NewPostgresStore(db *pgxpool.Pool) *PostgresStore {
	return &PostgresStore{db: db}
}

func (s *PostgresStore) CreateTeam(ctx context.Context, teamID, name, ownerEmail string) error {
	tx, err := s.db.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	_, err = tx.Exec(ctx, "INSERT INTO teams (id, name, owner_email, created_at) VALUES ($1, $2, $3, $4)",
		teamID, name, ownerEmail, float64(time.Now().Unix()))
	if err != nil {
		return err
	}

	_, err = tx.Exec(ctx, "INSERT INTO users (email, team_id, role, joined_at) VALUES ($1, $2, $3, $4)",
		ownerEmail, teamID, "ADMIN", float64(time.Now().Unix()))
	if err != nil {
		return err
	}

	return tx.Commit(ctx)
}

func (s *PostgresStore) GetUserRoleAndTeam(ctx context.Context, email string) (*domain.User, error) {
	var user domain.User
	err := s.db.QueryRow(ctx, "SELECT role, team_id FROM users WHERE email = $1", email).Scan(&user.Role, &user.TeamID)
	if err != nil {
		return nil, err
	}
	return &user, nil
}
