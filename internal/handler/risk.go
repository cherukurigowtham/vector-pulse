package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"time"
	"vector-pulse/internal/domain"
	"vector-pulse/internal/middleware"
	"vector-pulse/internal/repository"
	"vector-pulse/internal/service"
)

type RiskHandler struct {
	riskSvc *service.RiskService
	repo    repository.ReadWriter
}

func NewRiskHandler(riskSvc *service.RiskService, repo repository.ReadWriter) *RiskHandler {
	return &RiskHandler{
		riskSvc: riskSvc,
		repo:    repo,
	}
}

func (h *RiskHandler) ScanOrder(w http.ResponseWriter, r *http.Request) {
	var order domain.Order
	if err := json.NewDecoder(r.Body).Decode(&order); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	merchantEmail := r.Header.Get("X-Merchant-Email")
	teamID := r.Header.Get("X-Team-ID")
	if claims, ok := middleware.GetClaims(r.Context()); ok {
		merchantEmail = claims.Email
		teamID = claims.TeamID
	}

	ctx := domain.RiskContext{
		Order:          order,
		MerchantEmail:  merchantEmail,
		MerchantTeamID: teamID,
		Flags:          []string{},
		Impacts:        make(map[string]float64),
		TrustScore:     100.0,
	}

	result, err := h.riskSvc.Analyze(ctx)
	if err != nil {
		http.Error(w, "Risk analysis failed", http.StatusInternalServerError)
		return
	}

	if teamID != "" {
		dbCtx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		_ = h.repo.InsertRiskEvent(dbCtx, repository.RiskEvent{
			TeamID:   teamID,
			UID:      order.UID,
			Email:    order.Email,
			Amount:   order.Amt,
			Score:    result.Score,
			Decision: result.Decision,
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}
