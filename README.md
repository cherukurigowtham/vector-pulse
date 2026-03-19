# Vector-Pulse: High-Concurrency Fraud Detection Engine

A real-time anomaly detection system built with **Rust** and **Python**, leveraging **Redis** as a feature store. This project demonstrates high-performance systems engineering applied to financial security.

## 🚀 The Architecture


* **Compute Engine (Rust)**: High-performance statistical analysis ($Z$-Score and Velocity math) compiled as a Python extension using `PyO3`.
* **Orchestration (Python)**: Real-time stream processing and decision-making logic.
* **Feature Store (Redis)**: Low-latency persistence for user reputations, sliding windows, and blacklists.
* **Infrastructure (Docker)**: Containerized microservices orchestrated via Docker Compose.

## 📊 Detection Logic
The system evaluates transactions using **Dynamic Thresholding**:
1.  **Statistical Outliers**: Calculates the Moving Average and Standard Deviation ($\sigma$) to determine the $Z$-Score.
    $$Z = \frac{|x - \mu|}{\sigma}$$
2.  **Temporal Velocity**: Detects bot-like behavior by measuring the time-delta between incoming requests.
3.  **Salted Hashing**: API keys are hashed using PBKDF2 with unique salts, protecting against rainbow table attacks.

## 🛠️ Tech Stack
* **Language**: Rust (Performance), Python (Logic)
* **Database**: Redis, PostgreSQL (Audit), SQLite (Local Fallback)
* **Tooling**: Docker, Maturin, PyO3, Pydantic, FastAPI

## 🏗️ Local Deployment
```bash
# Copy the example environment and adjust values if needed
cp .env.example .env

# Build and launch the cluster (API + Redis + Postgres audit store)
docker-compose up --build

# Monitor live Redis keys
docker exec -it [redis-container-id] redis-cli KEYS *
```

The local Docker stack now starts:
- Redis for live fraud state
- Postgres for audit persistence
- the API wired to both services

That gives local behavior much closer to production than the old Redis-only setup.

## 🧪 Local Checks
```bash
# Run the automated backend regression suite
python3 -m unittest discover -s tests -p 'test_*.py'

# Run the demo client against a local API
export VECTOR_PULSE_API_KEY=vp_your_key_here
python3 scripts/demo_client.py
```

## ⚙️ Runtime Tuning
```bash
# Examples: tune fraud thresholds without editing code
export RISK_DECISION_THRESHOLD=45
export RISK_VELOCITY_MAX_ORDERS=4
export RISK_WEIGHT_SYBIL=30
export RISK_SAVINGS_PER_BLOCK_INR=90
export RISK_FAIL_CLOSED=true # Set to true to block orders if risk analysis fails/times out

# Redis State Isolation (Phase 2)
export REDIS_PREFIX=vp:prod
# All Redis keys will be prefixed as: {REDIS_PREFIX}:v1:{key}
```

## 🗄️ Audit Storage
```bash
# Default: SQLite audit log in audit_log.db

# Optional: use Postgres for audit persistence in multi-worker production
export DATABASE_URL=postgresql://user:password@host:5432/vector_pulse
```

When `DATABASE_URL` is set, `risk_audit` and `risk_profile_audit` use Postgres. Without it, the app falls back to SQLite.

## 🚢 Production Environment
```bash
export ADMIN_SECRET_KEY=replace_me
export ADMIN_EMAILS=admin1@example.com,admin2@example.com
export SESSION_COOKIE_SECURE=true
export CORS_ALLOW_ORIGINS=https://your-admin.example.com,https://your-app.example.com
export REDIS_HOST=your-redis-host
export REDIS_PORT=6379
export REDIS_PASSWORD=your-redis-password
export REDIS_SSL=true
export DATABASE_URL=postgresql://user:password@host:5432/vector_pulse
export PILOT_REQUEST_WEBHOOK_URL=https://hooks.example.com/vector-pulse-leads
```

Recommended production shape:
- Redis for live fraud state
- Postgres for audit persistence
- explicit `CORS_ALLOW_ORIGINS`
- generated or managed `ADMIN_SECRET_KEY`
- explicit `ADMIN_EMAILS`
- secure session cookies in production
- optional `PILOT_REQUEST_WEBHOOK_URL` for new lead notifications

The `/health` endpoint now reports both Redis and audit-backend status, including whether the audit layer is using `sqlite` or `postgres`. The `/readyz` endpoint is stricter and returns `503` if Redis or the audit backend is unavailable.

## 🛡️ Utility Scripts
```bash
# Flush Redis only when you confirm the action and provide the system secret
export VECTOR_PULSE_RESET_CONFIRM=DELETE_ALL_DATA
export VECTOR_PULSE_ADMIN_KEY=your_admin_secret_key # Must match ADMIN_SECRET_KEY
python3 scripts/admin_reset.py

## 🔑 API Key Management
The API now supports self-service key management via `/v1/security/auth/keys`:
- `GET /v1/security/auth/keys`: List all keys for your team.
- `POST /v1/security/auth/keys`: Generate a new API key.
- `DELETE /v1/security/auth/keys/{key_hash}`: Revoke a specific key.

All keys are stored securely using PBKDF2 hashing with unique salts.

## 🧠 Advanced ML Intelligence (Phase 3)
The engine now features a modular "Neural Orchestrator" that leverages:
- **Thompson Sampling (RL)**: Dynamic weight adjustments based on actual feedback loops.
- **Shield Mode**: Automated threshold tightening during high-volume attack waves.
- **Behavioral Transformers**: Sequence probability analysis to detect non-human interaction patterns.
- **Feature Store**: Real-time velocity acceleration and identity diversity metrics.

To simulate an attack and verify the adaptive resilience:
```bash
PYTHONPATH=. python3 tests/verify_ml_intelligence.py
```
