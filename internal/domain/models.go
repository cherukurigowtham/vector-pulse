package domain

type Order struct {
	UID   string  `json:"uid"`
	Amt   float64 `json:"amt"`
	Addr  string  `json:"addr"`
	Pin   string  `json:"pin"`
	Email string  `json:"email"`
	Phone string  `json:"phone"`
}

type RiskContext struct {
	Order          Order                  `json:"order"`
	MerchantEmail  string                 `json:"merchant_email"`
	MerchantTeamID string                 `json:"merchant_team_id"`
	Flags          []string               `json:"flags"`
	Impacts        map[string]float64     `json:"impacts"`
	Metadata       map[string]interface{} `json:"metadata"`
	TrustScore     float64                `json:"trust_score"`
}

type RiskResult struct {
	Score      float64            `json:"score"`
	Decision   string             `json:"decision"`
	Flags      []string           `json:"flags"`
	Impacts    map[string]float64 `json:"impacts"`
	TrustScore float64            `json:"trust_score"`
	RequestID  string             `json:"request_id"`
}

type UsageStats struct {
	MonthScans int    `json:"month_scans"`
	TotalScans int    `json:"total_scans"`
	Period     string `json:"period"`
}
