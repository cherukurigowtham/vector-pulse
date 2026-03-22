package service

import (
	"context"
	"fmt"
	"time"
	"vantix/internal/core"
	"vantix/internal/domain"
)

type UsageService struct {
	ctx context.Context
}

func NewUsageService() *UsageService {
	return &UsageService{
		ctx: context.Background(),
	}
}

func (s *UsageService) RecordScan(teamID string) error {
	now := time.Now()
	dayKey := fmt.Sprintf("usage:%s:scans:%s", teamID, now.Format("2006-01-02"))
	monthKey := fmt.Sprintf("usage:%s:scans:%s", teamID, now.Format("2006-01"))
	totalKey := fmt.Sprintf("usage:%s:scans:total", teamID)

	pipe := core.RDB.Pipeline()
	pipe.Incr(s.ctx, dayKey)
	pipe.Incr(s.ctx, monthKey)
	pipe.Incr(s.ctx, totalKey)
	
	// Set expiry (optional)
	pipe.Expire(s.ctx, dayKey, 40*24*time.Hour)
	pipe.Expire(s.ctx, monthKey, 400*24*time.Hour)

	_, err := pipe.Exec(s.ctx)
	return err
}

func (s *UsageService) GetTeamUsage(teamID string) (domain.UsageStats, error) {
	now := time.Now()
	monthKey := fmt.Sprintf("usage:%s:scans:%s", teamID, now.Format("2006-01"))
	totalKey := fmt.Sprintf("usage:%s:scans:total", teamID)

	monthScans, _ := core.RDB.Get(s.ctx, monthKey).Int()
	totalScans, _ := core.RDB.Get(s.ctx, totalKey).Int()

	return domain.UsageStats{
		MonthScans: monthScans,
		TotalScans: totalScans,
		Period:     now.Format("2006-01"),
	}, nil
}
