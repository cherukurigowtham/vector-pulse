import time
import logging
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from app.observability.tracing import init_tracing
from app.core.json_logger import configure_json_logging
from app.core.redis import r
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import ENVIRONMENT, CORS_ALLOW_ORIGINS, DATABASE_URL, AUDIT_DB

# Optional: JSON structured logging (enterprise-friendly)
try:
    from app.core.json_logger import configure_json_logging

    configure_json_logging()
except Exception:
    # If logger module is not available in this environment, skip gracefully
    pass
from app.db.database import AUDIT_STORE
from app.core.helpers import _log_event, PRIMARY_ADMIN_EMAIL, ADMIN_EMAILS
from app.routers import (
    public,
    webhooks,
    risk,
    admin,
    admin_dashboard,
    merchant,
    behavioral,
    compliance,
    forensics,
    marketplace,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Initialize DB
    await AUDIT_STORE.init()
    _log_event(
        "startup_complete",
        environment=ENVIRONMENT,
        audit_backend=AUDIT_STORE.backend,
        admin_count=len(ADMIN_EMAILS),
    )
    try:
        yield
    finally:
        await AUDIT_STORE.close()
        _log_event("shutdown_complete", environment=ENVIRONMENT)


app = FastAPI(
    title="Vantix RTO Shield API",
    description="Real-time fraud detection for Indian e-commerce. Stop RTO losses instantly.",
    version="1.0.0",
    lifespan=lifespan,
)
configure_json_logging()

# Initialize tracing (production-grade will export to OTLP)
init_tracing(
    app,
    service_name="vector_pulse_api",
    enable=(ENVIRONMENT in {"production", "staging"}),
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Admin-Key"],
)


# Security & Logging Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    _log_event(
        "http_request",
        request_id=request_id,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


@app.middleware("http")
async def force_https(request: Request, call_next):
    # Redirect to HTTPS in production behind a TLS-terminating load balancer
    try:
        proto = request.headers.get("x-forwarded-proto", "http").lower()
        if ENVIRONMENT == "production" and proto != "https":
            https_url = str(request.url).replace("http://", "https://", 1)
            from fastapi.responses import RedirectResponse

            return RedirectResponse(https_url)
    except Exception:
        pass
    return await call_next(request)


from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError


# Global Error Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "message": str(exc.detail),
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "code": 422,
            "message": "Validation Error",
            "details": exc.errors(),
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logging.error(f"Unhandled Exception [ID: {request_id}]: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "fail",
            "code": 500,
            "message": "An internal analysis service error occurred.",
            "request_id": request_id,
        },
    )


from app.core.edge_intelligence import EdgeIntelligenceMiddleware

app.add_middleware(EdgeIntelligenceMiddleware)

# Include Routers
app.include_router(public.router)
app.include_router(webhooks.router)
app.include_router(risk.router)
app.include_router(admin.router)
app.include_router(admin_dashboard.router)
app.include_router(merchant.router)
app.include_router(behavioral.router)
app.include_router(compliance.router)
app.include_router(forensics.router)
app.include_router(marketplace.router)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from app.observability.metrics import get_metrics
import os

# Serve Landing Page Static Files
landing_path = os.path.join(os.path.dirname(__file__), "..", "landing")
app.mount("/static", StaticFiles(directory=landing_path), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(landing_path, "index.html"))


@app.get("/merchant", include_in_schema=False)
async def serve_merchant():
    return FileResponse(os.path.join(landing_path, "merchant.html"))


@app.get("/admin-dashboard", include_in_schema=False)
async def serve_admin():
    return FileResponse(os.path.join(landing_path, "admin.html"))


@app.get("/health")
async def health():
    try:
        redis_ok = True
        try:
            redis_ok = await r.ping()
        except Exception:
            redis_ok = False
        db_ok = await AUDIT_STORE.healthcheck()
        db_status = "connected" if db_ok else "error"
        redis_status = "connected" if redis_ok else "disconnected"
        status = "ok" if (redis_ok and db_ok) else "degraded"
        return {"status": status, "redis": redis_status, "db": db_status}
    except Exception as e:
        return {"status": "error", "redis": "unknown", "db": "unknown", "error": str(e)}


@app.get("/readyz")
async def readyz():
    redis_ok = False
    db_ok = False
    try:
        redis_ok = await r.ping()
    except Exception:
        redis_ok = False
    try:
        db_ok = await AUDIT_STORE.healthcheck()
    except Exception:
        db_ok = False
    if redis_ok and db_ok:
        return {"status": "ready"}
    return JSONResponse(
        status_code=503, content={"status": "not_ready", "redis": redis_ok, "db": db_ok}
    )


@app.get("/metrics")
async def metrics():
    # Expose Prometheus-compatible metrics
    try:
        return Response(get_metrics(), media_type="text/plain")
    except Exception:
        # Fallback to a simple JSON if metrics export fails
        keys = [
            "stat:velocity",
            "stat:sybil",
            "stat:price",
            "stat:clusters",
            "stat:geoip",
            "total_blocks",
        ]
        from app.core.redis import r

        values = await r.mget(keys)
        metrics_data = {k: int(v or 0) for k, v in zip(keys, values)}
        return JSONResponse(metrics_data)
