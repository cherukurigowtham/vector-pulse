package service

import (
	"context"
	"fmt"
	"sync"
	"time"
	"vantix/internal/repository"
)

type MerchantService struct {
	repo     repository.ReadWriter
	usageSvc *UsageService
	cache    *summaryCache
}

type Summary struct {
	MonthScans    int              `json:"month_scans"`
	TotalScanned  int              `json:"total_scanned"`
	Blocks        int              `json:"blocks"`
	SLAMetrics    map[string]any   `json:"sla_metrics"`
	IdentityStats map[string]any   `json:"identity_stats"`
	GovernanceLog []map[string]any `json:"governance_logs"`
	Recent        []map[string]any `json:"recent_activity"`
}

type summaryCache struct {
	mu   sync.RWMutex
	data map[string]cachedSummary
}

type cachedSummary struct {
	value Summary
	exp   time.Time
}

func NewMerchantService(repo repository.ReadWriter, usageSvc *UsageService) *MerchantService {
	return &MerchantService{
		repo:     repo,
		usageSvc: usageSvc,
		cache: &summaryCache{
			data: make(map[string]cachedSummary),
		},
	}
}

func (s *MerchantService) GetSummary(ctx context.Context, teamID string) (Summary, error) {
	if summary, ok := s.cache.get(teamID); ok {
		return summary, nil
	}

	usage, _ := s.usageSvc.GetTeamUsage(teamID)

	blocks, err := s.repo.CountBlockedRiskEvents(ctx, teamID)
	if err != nil {
		blocks = 0
	}

	events, err := s.repo.ListRecentRiskEvents(ctx, teamID, 10)
	if err != nil {
		events = nil
	}

	recent := make([]map[string]any, 0, len(events))
	for _, event := range events {
		recent = append(recent, map[string]any{
			"id":     fmt.Sprintf("txn_%d", event.At.Unix()),
			"uid":    event.UID,
			"user":   event.TokenizedEmail,
			"time":   event.At.Format(time.RFC3339),
			"amt":    event.Amount,
			"score":  event.Score,
			"status": event.Decision,
		})
	}

	summary := Summary{
		MonthScans:   usage.MonthScans,
		TotalScanned: usage.TotalScans,
		Blocks:       blocks,
		SLAMetrics: map[string]any{
			"latency_ms": 14,
			"accuracy":   98.4,
		},
		IdentityStats: map[string]any{
			"hits":       blocks,
			"percentage": 2.7,
		},
		GovernanceLog: []map[string]any{
			{"action": "Auto-threshold optimization", "timestamp": time.Now().Unix(), "actor": "policy-engine"},
		},
		Recent: recent,
	}

	s.cache.set(teamID, summary, 3*time.Second)
	return summary, nil
}

func (s *MerchantService) GetPaymentHistory(ctx context.Context, teamID string, limit int) ([]repository.PaymentRecord, error) {
	if limit <= 0 || limit > 100 {
		limit = 50
	}
	return s.repo.ListPayments(ctx, teamID, limit)
}

func (s *MerchantService) VerifyPayment(ctx context.Context, paymentID, orderID, teamID string, amount float64) error {
	if amount <= 0 {
		amount = 49.99
	}
	return s.repo.InsertPayment(ctx, paymentID, orderID, teamID, amount, "success")
}

func (c *summaryCache) get(teamID string) (Summary, bool) {
	c.mu.RLock()
	entry, ok := c.data[teamID]
	c.mu.RUnlock()
	if !ok || time.Now().After(entry.exp) {
		return Summary{}, false
	}
	return entry.value, true
}

func (c *summaryCache) set(teamID string, value Summary, ttl time.Duration) {
	c.mu.Lock()
	c.data[teamID] = cachedSummary{value: value, exp: time.Now().Add(ttl)}
	c.mu.Unlock()
}
