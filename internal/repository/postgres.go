package repository

import (
	"context"
	"database/sql"
	"time"
)

type User struct {
	Email        string
	PasswordHash string
	TeamID       string
	Role         string
}

type RiskEvent struct {
	TeamID   string
	UID      string
	Email    string
	Amount   float64
	Score    float64
	Decision string
	At       time.Time
}

type PaymentRecord struct {
	PaymentID string
	Amount    float64
	Status    string
	Timestamp int64
}

type RiskEventSummary struct {
	UID      string
	Email    string
	Amount   float64
	Score    float64
	Decision string
	At       time.Time
}

type ReadWriter interface {
	CreateUser(ctx context.Context, user User) error
	GetUserByEmail(ctx context.Context, email string) (User, error)
	InsertRiskEvent(ctx context.Context, event RiskEvent) error
	CountBlockedRiskEvents(ctx context.Context, teamID string) (int, error)
	ListRecentRiskEvents(ctx context.Context, teamID string, limit int) ([]RiskEventSummary, error)
	ListPayments(ctx context.Context, teamID string, limit int) ([]PaymentRecord, error)
	InsertPayment(ctx context.Context, paymentID, orderID, teamID string, amount float64, status string) error
}

type PostgresRepository struct {
	db *sql.DB
}

func NewPostgresRepository(db *sql.DB) *PostgresRepository {
	return &PostgresRepository{db: db}
}

func (p *PostgresRepository) CreateUser(ctx context.Context, user User) error {
	_, err := p.db.ExecContext(ctx, `
		INSERT INTO users(email, password_hash, team_id, role)
		VALUES($1,$2,$3,$4)
	`, user.Email, user.PasswordHash, user.TeamID, user.Role)
	return err
}

func (p *PostgresRepository) GetUserByEmail(ctx context.Context, email string) (User, error) {
	var user User
	err := p.db.QueryRowContext(ctx, `
		SELECT email, password_hash, team_id, role
		FROM users WHERE email=$1
	`, email).Scan(&user.Email, &user.PasswordHash, &user.TeamID, &user.Role)
	return user, err
}

func (p *PostgresRepository) InsertRiskEvent(ctx context.Context, event RiskEvent) error {
	_, err := p.db.ExecContext(ctx, `
		INSERT INTO risk_events(team_id, uid, user_email, amount, score, decision)
		VALUES($1,$2,$3,$4,$5,$6)
	`, event.TeamID, event.UID, event.Email, event.Amount, event.Score, event.Decision)
	return err
}

func (p *PostgresRepository) CountBlockedRiskEvents(ctx context.Context, teamID string) (int, error) {
	var count int
	err := p.db.QueryRowContext(ctx, `
		SELECT COUNT(*) FROM risk_events
		WHERE team_id=$1 AND decision='BLOCK'
	`, teamID).Scan(&count)
	return count, err
}

func (p *PostgresRepository) ListRecentRiskEvents(ctx context.Context, teamID string, limit int) ([]RiskEventSummary, error) {
	rows, err := p.db.QueryContext(ctx, `
		SELECT uid, user_email, amount, score, decision, created_at
		FROM risk_events
		WHERE team_id=$1
		ORDER BY created_at DESC
		LIMIT $2
	`, teamID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := make([]RiskEventSummary, 0, limit)
	for rows.Next() {
		var item RiskEventSummary
		if scanErr := rows.Scan(&item.UID, &item.Email, &item.Amount, &item.Score, &item.Decision, &item.At); scanErr != nil {
			return nil, scanErr
		}
		result = append(result, item)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}
	return result, nil
}

func (p *PostgresRepository) ListPayments(ctx context.Context, teamID string, limit int) ([]PaymentRecord, error) {
	rows, err := p.db.QueryContext(ctx, `
		SELECT payment_id, amount, status, EXTRACT(EPOCH FROM created_at)::BIGINT
		FROM payments
		WHERE team_id=$1
		ORDER BY created_at DESC
		LIMIT $2
	`, teamID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := make([]PaymentRecord, 0, limit)
	for rows.Next() {
		var item PaymentRecord
		if scanErr := rows.Scan(&item.PaymentID, &item.Amount, &item.Status, &item.Timestamp); scanErr != nil {
			return nil, scanErr
		}
		result = append(result, item)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}
	return result, nil
}

func (p *PostgresRepository) InsertPayment(ctx context.Context, paymentID, orderID, teamID string, amount float64, status string) error {
	_, err := p.db.ExecContext(ctx, `
		INSERT INTO payments(payment_id, order_id, team_id, amount, status)
		VALUES($1,$2,$3,$4,$5)
	`, paymentID, orderID, teamID, amount, status)
	return err
}
