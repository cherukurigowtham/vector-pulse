package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"vantix/internal/config"
	"vantix/internal/core"
	"vantix/internal/db"
	"vantix/internal/handler"
	"vantix/internal/middleware"
	"vantix/internal/repository"
	"vantix/internal/service"

	"github.com/gorilla/mux"
)

func main() {
	// Initialize Configuration
	config.LoadConfig()

	// Initialize Infrastructure
	core.InitRedis()
	db.InitDB()
	defer db.CloseDB()

	// Initialize Services
	repo := repository.NewPostgresRepository(db.DB)
	usageSvc := service.NewUsageService()
	riskSvc := service.NewRiskService(usageSvc)
	authSvc := service.NewAuthService(repo)
	merchantSvc := service.NewMerchantService(repo, usageSvc)

	// Initialize Handlers
	riskHandler := handler.NewRiskHandler(riskSvc, repo)
	authHandler := handler.NewAuthHandler(authSvc)
	merchantHandler := handler.NewMerchantHandler(merchantSvc)

	// Setup Router
	r := mux.NewRouter()

	// Health Check
	r.Use(corsMiddleware)
	r.HandleFunc("/api/v1/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"status": "healthy", "engine": "golang"}`)
	}).Methods("GET")

	// API V1 Routes
	v1 := r.PathPrefix("/api/v1").Subrouter()

	// Auth
	v1.HandleFunc("/security/auth/signup", authHandler.Signup).Methods("POST", "OPTIONS")
	v1.HandleFunc("/security/auth/login", authHandler.Login).Methods("POST", "OPTIONS")
	v1.Handle("/security/auth/me", middleware.AuthMiddleware(http.HandlerFunc(authHandler.Me))).Methods("GET", "OPTIONS")
	v1.Handle("/security/auth/logout", middleware.AuthMiddleware(http.HandlerFunc(authHandler.Logout))).Methods("POST", "OPTIONS")

	// Merchant
	v1.Handle("/merchant/reporting/summary", middleware.AuthMiddleware(http.HandlerFunc(merchantHandler.Summary))).Methods("GET", "OPTIONS")
	v1.Handle("/merchant/payments/history", middleware.AuthMiddleware(http.HandlerFunc(merchantHandler.PaymentHistory))).Methods("GET", "OPTIONS")
	v1.Handle("/merchant/payments/orders", middleware.AuthMiddleware(http.HandlerFunc(merchantHandler.CreateOrder))).Methods("POST", "OPTIONS")
	v1.Handle("/merchant/payments/verify", middleware.AuthMiddleware(http.HandlerFunc(merchantHandler.VerifyOrder))).Methods("POST", "OPTIONS")

	// Risk scans (JWT or x-api-key)
	v1.Handle("/risk/scan", middleware.AuthMiddleware(http.HandlerFunc(riskHandler.ScanOrder))).Methods("POST", "OPTIONS")

	// Start Server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	log.Printf("Vantix Engine starting on port %s...", port)
	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

func corsMiddleware(next http.Handler) http.Handler {
	// Fallback origins for local development
	origins := []string{"http://localhost:3000", "http://127.0.0.1:3000", "https://portal-three-drab.vercel.app"}
	if len(config.GlobalConfig.CORSAllowOrigins) > 0 {
		origins = config.GlobalConfig.CORSAllowOrigins
	}

	allowOrigins := make(map[string]struct{}, len(origins))
	for _, origin := range origins {
		trimmed := strings.TrimSpace(origin)
		if trimmed != "" {
			allowOrigins[trimmed] = struct{}{}
		}
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if _, ok := allowOrigins[origin]; ok {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Vary", "Origin")
		} else if os.Getenv("ENVIRONMENT") != "production" {
			// In development, be helpful for local dev ports
			w.Header().Set("Access-Control-Allow-Origin", origin)
		}

		w.Header().Set("Access-Control-Allow-Credentials", "true")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
