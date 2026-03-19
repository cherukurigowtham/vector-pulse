package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/joho/godotenv"
	"github.com/redis/go-redis/v9"
	"vector-pulse/internal/handler"
	"vector-pulse/internal/repository"
	"vector-pulse/internal/service"
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
	
	pgStore := repository.NewPostgresStore(dbPool)
	redisStore := repository.NewRedisStore(redisClient)
	authService := service.NewAuthService(pgStore, redisStore)
	authHandler := handler.NewAuthHandler(authService)

	r := mux.NewRouter()

	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin != "" {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Credentials", "true")
				w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
				w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE")
			}

			if r.Method == "OPTIONS" {
				w.WriteHeader(http.StatusOK)
				return
			}

			next.ServeHTTP(w, r)
		})
	})

	api := r.PathPrefix("/api/v1/security/auth").Subrouter()
	api.HandleFunc("/signup", authHandler.Signup).Methods("POST", "OPTIONS")
	api.HandleFunc("/login", authHandler.Login).Methods("POST", "OPTIONS")
	api.HandleFunc("/logout", authHandler.Logout).Methods("POST", "OPTIONS")
	api.HandleFunc("/me", authHandler.Me).Methods("GET", "OPTIONS")

	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	log.Printf("Starting Golang API on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}
