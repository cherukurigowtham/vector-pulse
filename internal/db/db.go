package db

import (
	"database/sql"
	"log"
	"vantix/internal/config"

	_ "github.com/jackc/pgx/v5/stdlib"
)

var DB *sql.DB

// InitDB initializes the PostgreSQL connection.
func InitDB() {
	dsn := config.GlobalConfig.DatabaseURL
	if dsn == "" {
		log.Println("WARNING: DATABASE_URL not set. Database operations will fail.")
		return
	}

	var err error
	// Use pgx driver for PostgreSQL
	DB, err = sql.Open("pgx", dsn)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}

	// Configure connection pool for production
	DB.SetMaxOpenConns(25)
	DB.SetMaxIdleConns(5)

	err = DB.Ping()
	if err != nil {
		log.Fatalf("Database ping failed: %v", err)
	}

	if err := ensureSchema(); err != nil {
		log.Fatalf("Database schema bootstrap failed: %v", err)
	}

	log.Println("Connected to PostgreSQL successfully.")
}

func CloseDB() {
	if DB != nil {
		DB.Close()
	}
}

func ensureSchema() error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS users (
			email TEXT PRIMARY KEY,
			password_hash TEXT NOT NULL,
			team_id TEXT NOT NULL,
			role TEXT NOT NULL DEFAULT 'ADMIN',
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
		)`,
		`CREATE TABLE IF NOT EXISTS payments (
			payment_id TEXT PRIMARY KEY,
			order_id TEXT NOT NULL,
			team_id TEXT NOT NULL,
			amount NUMERIC(12,2) NOT NULL,
			status TEXT NOT NULL,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
		)`,
		`CREATE TABLE IF NOT EXISTS risk_events (
			id BIGSERIAL PRIMARY KEY,
			team_id TEXT NOT NULL,
			uid TEXT,
			user_email TEXT,
			amount NUMERIC(12,2),
			score DOUBLE PRECISION,
			decision TEXT,
			created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
		)`,
		`CREATE INDEX IF NOT EXISTS idx_risk_events_team_created ON risk_events(team_id, created_at DESC)`,
		`CREATE INDEX IF NOT EXISTS idx_payments_team_created ON payments(team_id, created_at DESC)`,
	}

	for _, stmt := range stmts {
		if _, err := DB.Exec(stmt); err != nil {
			return err
		}
	}
	return nil
}
