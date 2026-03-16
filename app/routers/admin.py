import time
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from app.models import AdminSessionRequest, RiskConfigUpdateRequest, PilotRequestStatusUpdate, PilotRequestDetailUpdate, UpgradeRequestDecision
from app.core.config import RISK_CONFIG, RATE_LIMITS
from app.core.redis import r
from app.db.database import AUDIT_STORE
from app.core.helpers import (
    ADMIN_KEY, PRIMARY_ADMIN_EMAIL, _is_admin_email, _resolve_risk_config, 
    _validate_risk_value, _coerce_risk_value, _has_custom_risk_profile, 
    _find_key_hash_by_email, _log_risk_profile_change, _log_event, _key_preview
)
from app.core.security import require_admin, _create_session, require_csrf

router = APIRouter(prefix="/v1/admin", tags=["admin"])

@router.post("/session", summary="Create an admin session")
async def create_admin_session(req: AdminSessionRequest, response: Response, request: Request):
    if req.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin credentials")
    await _create_session(PRIMARY_ADMIN_EMAIL, response, request)
    return {"message": "Admin session created"}

@router.post("/risk-config/{email}", summary="Update a user's merchant-specific risk profile")
async def update_risk_config(email: str, req: RiskConfigUpdateRequest, admin_actor: str = Depends(require_admin)):
    key_hash = await _find_key_hash_by_email(email)
    if not key_hash:
        raise HTTPException(status_code=404, detail="User API key profile not found")
    profile = await r.hgetall(f"apikey:{key_hash}")
    previous_config = _resolve_risk_config(profile)
    payload = req.model_dump(exclude_none=True)
    updates = {}
    for name, value in payload.items():
        coerced = _validate_risk_value(name, _coerce_risk_value(name, value))
        updates[f"risk_{name}"] = str(coerced)
    if updates:
        await r.hset(f"apikey:{key_hash}", mapping=updates)
    new_profile = await r.hgetall(f"apikey:{key_hash}")
    new_config = _resolve_risk_config(new_profile)
    await _log_risk_profile_change(email, admin_actor, "UPDATE", previous_config, new_config)
    return {"email": email, "risk_profile": new_config, "is_custom": _has_custom_risk_profile(new_profile)}

@router.get("/users", summary="List all registered API keys and their usage")
async def get_all_users(_: str = Depends(require_admin)):
    keys = await r.smembers("admin:all_keys")
    users = []
    current_month = time.strftime('%Y-%m')
    for key_hash in keys:
        key_data = await r.hgetall(f"apikey:{key_hash}")
        if not key_data: continue
        email = key_data.get("email", "unknown")
        if _is_admin_email(email): continue
        usage = int(await r.get(f"usage:{key_hash}:{current_month}") or 0)
        users.append({
            "email": email,
            "api_key_preview": _key_preview(key_data.get("key_prefix"), key_data.get("key_suffix")),
            "plan": key_data.get("plan", "free"),
            "usage_this_month": usage,
            "limit": RATE_LIMITS.get(key_data.get("plan", "free"), 1_000),
            "risk_profile": _resolve_risk_config(key_data),
            "is_custom_risk_profile": _has_custom_risk_profile(key_data),
        })
    users.sort(key=lambda x: x["usage_this_month"], reverse=True)
    return {"users": users, "total_users": len(users)}

@router.get("/pilot-analytics", summary="Summarize pilot lead funnel and mix")
async def get_pilot_analytics(_: str = Depends(require_admin)):
    emails = await r.smembers("pilot_request_emails")
    leads = [await r.hgetall(f"pilot_request:{e}") for e in emails if e]
    # Simplified logic for extraction, would be expanded with actual status counting
    return {"total": len(leads), "leads": leads}
