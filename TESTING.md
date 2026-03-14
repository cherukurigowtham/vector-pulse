# 🧪 Vector-Pulse Testing Guide

This document describes how to run the various test suites for Vector-Pulse.

## CI Coverage
GitHub Actions now runs:
- unit and frontend-contract tests on every push and pull request
- live integration tests against Redis and Postgres services
- Playwright dashboard tests after integration passes

The app-focused workflow lives in [.github/workflows/app-ci.yml](/Users/gowthamcherukuri/Desktop/vector_pulse/.github/workflows/app-ci.yml).

## 1. Unit Tests
Fast, logic-only tests with mocks. Does not require external services.
```bash
python3 -m unittest tests/test_api_gateway.py
```

## 2. Live Integration Tests
Requires Docker. Verifies that the API gateway correctly interacts with real Redis and Postgres instances.
```bash
# Automate setup, run, and teardown
chmod +x scripts/run_integration.sh
./scripts/run_integration.sh
```
Or manually:
1. `docker-compose up -d redis_store postgres_audit`
2. `export REDIS_HOST=localhost`
3. `export DATABASE_URL=postgresql://vector_pulse:vector_pulse@localhost:5432/vector_pulse`
4. `export VECTOR_PULSE_API_URL=http://localhost:8000`
5. `pytest tests/integration_live.py`

The live integration suite now verifies:
- Redis connectivity
- `/health` dependency reporting
- merchant registration
- authenticated risk checks
- explain-cache writes
- admin session access
- outcome updates

## 3. E2E Browser Tests (Playwright)
Verifies the Admin Dashboard interface. Requires Playwright.
```bash
# Install dependencies
pip install pytest-playwright
playwright install

# Run tests (ensure API is running at localhost:8000)
pytest tests/e2e/test_dashboard.py
```

The E2E suite seeds its own merchant and risk event before running. It covers:
- admin login success/failure
- dashboard load
- profile modal visibility
- explain modal visibility

## 4. Infrastructure Verification
Check if your `DATABASE_URL` or local `audit_log.db` is healthy.
```bash
python3 scripts/verify_db.py
```

---

## Service Configuration for Tests
| Environment Variable | Local Dev Default |
|----------------------|-------------------|
| `REDIS_HOST` | `localhost` |
| `DATABASE_URL` | `postgresql://vector_pulse:vector_pulse@localhost:5432/vector_pulse` |
| `ADMIN_SECRET_KEY` | `local-dev-admin-key` |
