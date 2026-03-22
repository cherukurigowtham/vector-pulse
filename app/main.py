import asyncio
import os
import sentry_sdk
from fastapi import FastAPI, Request
from app.api.v1.risk import analysis as risk_analysis
from app.api.v1.risk import forensics
from app.api.v1.merchant import profile, team, reporting, billing
from app.api.v1.security import auth, vault
from app.api.v1.health import router as health_router
from app.api.v1 import ops as ops_router
from app.routers import public, merchant, stream
from app.core.config import CORS_ALLOW_ORIGINS
from app.core.logger import setup_logging
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import AUDIT_STORE
from app.core.security import verify_jwt
from app.services.discovery.consortium import ConsortiumRing
from app.workers.audit_flusher import run_audit_flusher
from app.services.monitoring.alerter import alerter
from app.services.monitoring.self_healing_service import self_healing_service

# === Boot: Structured Logging ===
setup_logging(service_name="vantix-api")

# === Boot: Sentry Error Tracking ===
_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        traces_sample_rate=0.1,   # 10% of requests traced for performance
        send_default_pii=False,   # GDPR: never send raw PII to Sentry
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    await AUDIT_STORE.init()
    consortium_thread = ConsortiumRing.attach_listener()
    flusher_task = asyncio.create_task(run_audit_flusher())
    yield
    flusher_task.cancel()
    try:
        await flusher_task
    except asyncio.CancelledError:
        pass
    if consortium_thread:
        consortium_thread.stop()
    await AUDIT_STORE.close()

app = FastAPI(
    title="Vantix RTO Shield - Google-Style Refactor",
    version="2.0.0",
    lifespan=lifespan
)

# Authentication Middleware (Populates request.state.user from JWT)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    token = request.cookies.get("vp_token")
    if token:
        user = verify_jwt(token)
        if user:
            request.state.user = user
    return await call_next(request)

# === Sovereign Operator: Global Exception Bridge ===
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 1. Autonomous Triage: Attempt Self-Healing for known patterns
    error_str = str(exc).upper()
    healing_pattern = None
    if "CACHE" in error_str or "REDIS" in error_str:
        healing_pattern = "CACHE_PRESSURE"
    elif "LATENCY" in error_str or "TIMEOUT" in error_str:
        healing_pattern = "HIGH_LATENCY"
    
    if healing_pattern:
        await self_healing_service.handle_anomaly(healing_pattern, {"error": str(exc)})
    else:
        # 2. Escalation: Dispatch critical alert to solo developer for unknown anomalies
        await alerter.send_critical(
            "UNKNOWN_SYSTEM_ANOMALY",
            str(exc),
            {"path": request.url.path, "method": request.method}
        )
    
    # Professional fallback
    raise exc

# Professional CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router, prefix="/api/v1")
app.include_router(merchant.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")
app.include_router(risk_analysis.router, prefix="/api/v1")
app.include_router(forensics.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(vault.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(team.router, prefix="/api/v1")
app.include_router(reporting.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(ops_router.router, prefix="/api/v1")
app.include_router(health_router)
