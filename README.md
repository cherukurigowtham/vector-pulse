# Vantix

Production-ready fraud intelligence platform with:
- Go backend API
- Next.js frontend portal
- PostgreSQL (system of record)
- Redis (high-speed counters and usage telemetry)

## Architecture

Backend follows a layered, interface-driven design:
- `handler` layer: HTTP transport concerns only
- `service` layer: business logic and orchestration
- `repository` layer: Postgres data access

This keeps core logic testable and enables storage/runtime swaps without handler rewrites.

## Key Backend Endpoints

- `POST /api/v1/security/auth/signup`
- `POST /api/v1/security/auth/login`
- `GET /api/v1/security/auth/me`
- `POST /api/v1/security/auth/logout`
- `POST /api/v1/risk/scan`
- `GET /api/v1/merchant/reporting/summary`
- `GET /api/v1/merchant/payments/history`
- `POST /api/v1/merchant/payments/orders`
- `POST /api/v1/merchant/payments/verify`
- `GET /api/v1/health`

## Performance Choices

- Deterministic risk scoring (no random hot path) for predictable latency.
- Connection-pooled Postgres access with schema bootstrap at startup.
- Redis pipeline usage for low-latency counter updates.
- Short-lived in-memory summary cache to reduce repeated dashboard query load.
- Context timeouts on DB-bound handlers to cap tail latency.

## Local Run

### 1) Start dependencies

Run Postgres and Redis locally (or use managed services), then configure `.env`.

### 2) Backend

```bash
cp .env.example .env
go run ./cmd/server
```

### 3) Frontend

```bash
cd portal
npm ci
npm run dev
```

Set frontend API target:

```bash
export NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Build Validation

```bash
GOCACHE=/tmp/go-build go test ./...
cd portal && npm run build
```
