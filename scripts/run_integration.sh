#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  echo "docker-compose or docker compose is required."
  exit 1
fi

if ! command -v pytest >/dev/null 2>&1; then
  echo "pytest is required to run live integration tests."
  exit 1
fi

cleanup() {
  if [ -n "${API_PID:-}" ]; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "Starting integration test environment..."
$COMPOSE_CMD up -d redis_store postgres_audit

export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_SSL="${REDIS_SSL:-false}"
export DATABASE_URL="${DATABASE_URL:-postgresql://vector_pulse:vector_pulse@localhost:5432/vector_pulse}"
export ADMIN_SECRET_KEY="${ADMIN_SECRET_KEY:-local-dev-admin-key}"
export VECTOR_PULSE_API_URL="${VECTOR_PULSE_API_URL:-http://localhost:8000}"
export PYTHONPATH=.

if ! curl -fsS "$VECTOR_PULSE_API_URL/health" >/dev/null 2>&1; then
  echo "Starting API gateway locally for integration tests..."
  uvicorn api_gateway:app --host 0.0.0.0 --port 8000 &
  API_PID=$!
fi

echo "Waiting for API health endpoint..."
for _ in $(seq 1 30); do
  if curl -fsS "$VECTOR_PULSE_API_URL/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS "$VECTOR_PULSE_API_URL/health" >/dev/null 2>&1; then
  echo "API did not become healthy in time."
  exit 1
fi

echo "Verifying infrastructure..."
python3 scripts/verify_db.py

echo "Running live integration tests..."
pytest tests/integration_live.py

echo "Live integration tests completed."
