package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"time"
	"vantix/internal/middleware"
	"vantix/internal/service"
)

type MerchantHandler struct {
	merchantService *service.MerchantService
}

type paymentOrderRequest struct {
	Amount float64 `json:"amount"`
}

type paymentVerifyRequest struct {
	OrderID   string `json:"razorpay_order_id"`
	PaymentID string `json:"razorpay_payment_id"`
	Signature string `json:"razorpay_signature"`
}

func NewMerchantHandler(merchantService *service.MerchantService) *MerchantHandler {
	return &MerchantHandler{merchantService: merchantService}
}

func (h *MerchantHandler) Summary(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaims(r.Context())
	if !ok {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	summary, err := h.merchantService.GetSummary(ctx, claims.TeamID)
	if err != nil {
		http.Error(w, "Unable to load summary", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusOK, summary)
}

func (h *MerchantHandler) PaymentHistory(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaims(r.Context())
	if !ok {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	history, err := h.merchantService.GetPaymentHistory(ctx, claims.TeamID, 50)
	if err != nil {
		http.Error(w, "Unable to load payment history", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{"history": history})
}

func (h *MerchantHandler) CreateOrder(w http.ResponseWriter, r *http.Request) {
	_, ok := middleware.GetClaims(r.Context())
	if !ok {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req paymentOrderRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.Amount <= 0 {
		req.Amount = 49.99
	}

	orderID := fmt.Sprintf("order_%d", time.Now().UnixNano())
	writeJSON(w, http.StatusOK, map[string]any{
		"id":     orderID,
		"amount": req.Amount,
		"status": "created",
	})
}

func (h *MerchantHandler) VerifyOrder(w http.ResponseWriter, r *http.Request) {
	claims, ok := middleware.GetClaims(r.Context())
	if !ok {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req paymentVerifyRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.PaymentID == "" {
		req.PaymentID = fmt.Sprintf("pay_%d", rand.Int63())
	}
	if req.OrderID == "" {
		req.OrderID = fmt.Sprintf("order_%d", time.Now().UnixNano())
	}

	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := h.merchantService.VerifyPayment(ctx, req.PaymentID, req.OrderID, claims.TeamID, 49.99); err != nil {
		http.Error(w, "Unable to persist payment", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"status":     "success",
		"payment_id": req.PaymentID,
	})
}

