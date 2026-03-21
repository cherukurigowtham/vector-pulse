package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"vector-pulse/internal/config"
	"vector-pulse/internal/core"
	"vector-pulse/internal/db"
	"vector-pulse/internal/handler"
	"vector-pulse/internal/middleware"
	"vector-pulse/internal/repository"
	"vector-pulse/internal/service"

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
	v1.HandleFunc("/security/auth/signup", authHandler.Signup).Methods("POST")
	v1.HandleFunc("/security/auth/login", authHandler.Login).Methods("POST")
	v1.Handle("/security/auth/me", middleware.AuthMiddleware(http.HandlerFunc(authHandler.Me))).Methods("GET")
	v1.Handle("/security/auth/logout", middleware.AuthMiddleware(http.HandlerFunc(authHandler.Logout))).Methods("POST")

	// Merchant
	v1.Handle("/merchant/reporting/summary", middleware.AuthMiddleware(http.HandlerFunc(merchantHandler.Summary))).Methods("GET")
	v1.Handle("/merchant/payments/history", middleware.AuthMiddleware(http.HandlerFunc(merchantHandler.PaymentHistory))).Methods("GET")
	v1.Handle("/merchant/payments/orders", middleware.AuthMiddleware(http.HandlerFunc(merchantHandler.CreateOrder))).Methods("POST")
	v1.Handle("/merchant/payments/verify", middleware.AuthMiddleware(http.HandlerFunc(merchantHandler.VerifyOrder))).Methods("POST")

	// Risk scans (JWT or x-api-key)
	v1.Handle("/risk/scan", middleware.AuthMiddleware(http.HandlerFunc(riskHandler.ScanOrder))).Methods("POST")

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
	allowOrigins := make(map[string]struct{}, len(config.GlobalConfig.CORSAllowOrigins))
	for _, origin := range config.GlobalConfig.CORSAllowOrigins {
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
		}
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
