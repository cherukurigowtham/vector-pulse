package vantix

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

const (
	DefaultBaseURL = "https://api.vantix.ai"
	Version        = "0.1.0"
)

type Client struct {
	APIKey     string
	HTTPClient *http.Client
	BaseURL    string
}

type Order struct {
	UID               string  `json:"uid"`
	Amt               float64 `json:"amt"`
	Email             string  `json:"email"`
	Phone             string  `json:"phone,omitempty"`
	Addr              string  `json:"addr"`
	PIN               string  `json:"pin,omitempty"`
	IP                string  `json:"ip"`
	DeviceHash        string  `json:"device_hash,omitempty"`
	CheckoutTimeSecs  float64 `json:"checkout_time_secs,omitempty"`
	KeystrokeVelocity float64 `json:"keystroke_velocity,omitempty"`
}

type RiskResult struct {
	Score      float64           `json:"score"`
	Decision   string            `json:"decision"`
	Flags      []string          `json:"flags"`
	TrustScore float64           `json:"trust_score"`
	Impacts    map[string]float64 `json:"xai_impacts"`
}

func NewClient(apiKey string) *Client {
	return &Client{
		APIKey: apiKey,
		HTTPClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		BaseURL: DefaultBaseURL,
	}
}

func (c *Client) Analyze(ctx context.Context, order Order) (*RiskResult, error) {
	url := fmt.Sprintf("%s/v1/risk/analyze", c.BaseURL)
	
	body, err := json.Marshal(order)
	if err != nil {
		return nil, err
	}
	
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Key", c.APIKey)
	req.Header.Set("User-Agent", fmt.Sprintf("vantix-go/%s", Version))
	
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("vantix api error: status %d", resp.StatusCode)
	}
	
	var result RiskResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	
	return &result, nil
}
