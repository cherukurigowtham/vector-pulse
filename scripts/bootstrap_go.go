package main

import (
	"context"
	"log"
	"os"
	"vector-pulse/internal/core"
	"vector-pulse/internal/repository"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/joho/godotenv"
	"github.com/redis/go-redis/v9"
)

func main() {
	godotenv.Load()

	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		log.Fatal("DATABASE_URL must be set")
	}
	dbPool, err := pgxpool.New(context.Background(), dbURL)
	if err != nil {
		log.Fatal(err)
	}
	defer dbPool.Close()

	redisHost := os.Getenv("REDIS_HOST")
	if redisHost == "" {
		redisHost = "localhost"
	}
	redisClient := redis.NewClient(&redis.Options{
		Addr: redisHost + ":6379",
	})
	
	email := "admin@vantix.ai"
	password := "admin123"
	
	salt, _ := core.GenerateSalt()
	pwdHash := core.HashPassword(password, salt)
	teamID := "admin-team"

	log.Printf("Bootstrapping admin account: %s", email)

	// Create in Postgres
	pgStore := repository.NewPostgresStore(dbPool)
	err = pgStore.CreateTeam(context.Background(), teamID, "Admin Team", email)
	if err != nil {
		log.Printf("Postgres error (might already exist): %v", err)
	}

	// Create in Redis
	redisStore := repository.NewRedisStore(redisClient)
	err = redisStore.HSet(context.Background(), "user:"+email, map[string]interface{}{
		"pwd_hash": pwdHash,
		"salt":     salt,
		"role":     "ADMIN",
		"team_id":  teamID,
	})
	if err != nil {
		log.Fatal(err)
	}

	log.Println("Admin bootstrap complete.")
}
