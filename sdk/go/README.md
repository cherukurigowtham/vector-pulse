# Vantix Go SDK (Beta)

High-performance, type-safe Go client for the Vantix RTO Shield.

## Installation

```bash
go get github.com/vantix-pulse/vantix-go
```

## Quick Start

```go
package main

import (
    "context"
    "fmt"
    "github.com/vantix-pulse/vantix-go"
)

func main() {
    client := vantix.NewClient("your_api_key")
    
    order := vantix.Order{
        UID:   "user_123",
        Email: "fraud@example.com",
        Amount: 5000.0,
        IP:    "1.2.3.4",
    }
    
    res, err := client.Analyze(context.Background(), order)
    if err != nil {
        panic(err)
    }
    
    fmt.Printf("Risk Score: %f\nDecision: %s\n", res.Score, res.Decision)
}
```
