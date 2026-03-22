package domain

import "time"

type User struct {
	Email     string    `json:"email"`
	TeamID    string    `json:"team_id"`
	Role      string    `json:"role"`
	JoinedAt  time.Time `json:"joined_at"`
}

type Team struct {
	ID         string    `json:"id"`
	Name       string    `json:"name"`
	OwnerEmail string    `json:"owner_email"`
	CreatedAt  time.Time `json:"created_at"`
}

type AuthRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type AuthResponse struct {
	Message string `json:"message"`
	APIKey  string `json:"api_key,omitempty"`
	Status  string `json:"status,omitempty"`
}
