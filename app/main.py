import time
import logging
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import ENVIRONMENT, CORS_ALLOW_ORIGINS, DATABASE_URL, AUDIT_DB
from app.db.database import AUDIT_STORE
from app.core.helpers import _log_event, PRIMARY_ADMIN_EMAIL, ADMIN_EMAILS
from app.routers import risk, admin, merchant, public

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
    _log_event("http_request", request_id=request_id, path=request.url.path, status_code=response.status_code, duration_ms=duration_ms)
    return response

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
            "request_id": getattr(request.state, "request_id", "unknown")
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
            "request_id": getattr(request.state, "request_id", "unknown")
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
            "request_id": request_id
        },
    )

# Include Routers
app.include_router(public.router)
app.include_router(risk.router)
app.include_router(admin.router)
app.include_router(merchant.router)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
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
    db_ok = await AUDIT_STORE.healthcheck()
    return {"status": "ok", "db": "connected" if db_ok else "error"}

@app.get("/metrics")
async def metrics():
    # Expose global stats for monitoring
    keys = ["stat:velocity", "stat:sybil", "stat:price", "stat:clusters", "stat:geoip", "total_blocks"]
    from app.core.redis import r
    values = await r.mget(keys)
    metrics_data = {k: int(v or 0) for k, v in zip(keys, values)}
    return metrics_data
