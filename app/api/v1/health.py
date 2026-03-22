"""
Health Check Endpoint
=====================
Provides a structured status report of all critical infrastructure dependencies.
Used by uptime monitors (UptimeRobot, BetterStack, etc.) and Kubernetes liveness probes.
"""
from fastapi import APIRouter
from app.core.redis import r
import time

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("", summary="Infrastructure health check")
async def health_check():
    status = {
        "status": "ok",
        "timestamp": time.time(),
        "services": {}
    }

    # --- Redis Check ---
    try:
        r.ping()
        status["services"]["redis"] = {"status": "ok"}
    except Exception as e:
        status["services"]["redis"] = {"status": "error", "detail": str(e)}
        status["status"] = "degraded"

    # --- Database Check ---
    try:
        from app.db.database import AUDIT_STORE
        is_ok = await AUDIT_STORE.healthcheck()
        status["services"]["database"] = {"status": "ok" if is_ok else "error"}
        if not is_ok:
            status["status"] = "degraded"
    except Exception as e:
        status["services"]["database"] = {"status": "error", "detail": str(e)}
        status["status"] = "degraded"

    return status
