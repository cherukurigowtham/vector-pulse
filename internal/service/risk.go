package service

import (
	"fmt"
	"hash/fnv"
	"math"
	"sync/atomic"
	"vector-pulse/internal/domain"
)

type RiskService struct {
	usageSvc *UsageService
	seq      uint64
}

func NewRiskService(usageSvc *UsageService) *RiskService {
	return &RiskService{
		usageSvc: usageSvc,
	}
}

func (s *RiskService) Analyze(ctx domain.RiskContext) (domain.RiskResult, error) {
	// Record Usage
	if ctx.MerchantTeamID != "" {
		_ = s.usageSvc.RecordScan(ctx.MerchantTeamID)
	}

	score := scoreOrder(ctx.Order)
	decision := "ALLOW"
	if score > 70 {
		decision = "BLOCK"
	} else if score > 40 {
		decision = "REVIEW"
	}

	seq := atomic.AddUint64(&s.seq, 1)
	result := domain.RiskResult{
		Score:      score,
		Decision:   decision,
		Flags:      ctx.Flags,
		Impacts:    ctx.Impacts,
		TrustScore: ctx.TrustScore,
		RequestID:  fmt.Sprintf("go_scan_%d", seq),
	}

	return result, nil
}

func scoreOrder(order domain.Order) float64 {
	base := 12.0

	// Amount impact: steeper increase for larger order values.
	base += math.Min(order.Amt/50.0, 35.0)

	// Sparse identity data often indicates risky traffic.
	if order.Email == "" {
		base += 12
	}
	if order.Phone == "" {
		base += 10
	}
	if len(order.Addr) < 12 {
		base += 8
	}
	if len(order.Pin) < 6 {
		base += 7
	}

	// Stable hash-based jitter to avoid ties while remaining deterministic.
	hasher := fnv.New32a()
	_, _ = hasher.Write([]byte(order.UID + "|" + order.Email + "|" + order.Pin))
	jitter := float64(hasher.Sum32()%1200) / 100.0
	base += jitter

	return math.Max(0, math.Min(base, 100))
}
