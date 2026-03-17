import time
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from app.models import Order, RiskConfigUpdateRequest, MerchantSettingsUpdate, UpgradeRequest, WebhookSettingsUpdate, AutomationRulesUpdate
from app.core.config import RISK_CONFIG, RATE_LIMITS
from app.core.redis import r
from app.db.database import AUDIT_STORE
from app.core.helpers import (
    _resolve_risk_config, _validate_risk_value, _coerce_risk_value, 
    _has_custom_risk_profile, _log_risk_profile_change, _log_event,
    _find_key_hash_by_email, _key_preview, _is_admin_email
)
from app.core.security import require_api_key, require_admin, require_csrf, role_required, get_current_user_role
from app.services.action_engine import ActionEngine

engine = ActionEngine(r)

router = APIRouter(prefix="/v1", tags=["merchant"])

@router.get("/auth/me", summary="Get the current logged in user's profile and API key")
async def auth_me(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")
        
    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
        
    current_month = time.strftime('%Y-%m')
    key_hash = user_data.get("key_hash") or await _find_key_hash_by_email(email)
    
    # preview logic
    key_profile = await r.hgetall(f"apikey:{key_hash}") if key_hash else {}
    preview = _key_preview(
        user_data.get("key_prefix") or key_profile.get("key_prefix"),
        user_data.get("key_suffix") or key_profile.get("key_suffix")
    )
    
    async with r.pipeline() as pipe:
        pipe.get(f"usage:{key_hash}:{current_month}" if key_hash else "usage:missing")
        pipe.get(f"savings:{email}")
        res = await pipe.execute()
    
    usage = int(res[0] or 0)
    savings = float(res[1] or 0)
    plan = user_data.get("plan", "free")
    limit = RATE_LIMITS.get(plan, 1000)

    return {
        "email": email,
        "role": user_data.get("role", "ANALYST"),
        "api_key": preview,
        "is_admin": _is_admin_email(email) or user_data.get("role") == "ADMIN",
        "risk_profile": _resolve_risk_config(key_profile) if key_hash else dict(RISK_CONFIG),
        "metrics": {
            "usage": usage,
            "limit": limit,
            "savings": savings,
            "plan": plan.upper(),
            "last_latency": float(await r.get(f"stats:latency:{email}") or 0),
            "pct": min(100, round((usage / limit) * 100)) if limit > 0 else 0
        }
    }

@router.get("/auth/reporting", summary="Get merchant-facing reporting for the Signal Hub")
async def auth_reporting(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    current_month = time.strftime("%Y-%m")
    key_hash = user_data.get("key_hash") or await _find_key_hash_by_email(email)
    async with r.pipeline() as pipe:
        pipe.get(f"usage:{key_hash}:{current_month}" if key_hash else "usage:missing")
        pipe.get(f"savings:{email}")
        res = await pipe.execute()

    usage = int(res[0] or 0)
    savings = float(res[1] or 0)
    recent_rows = await AUDIT_STORE.fetch_recent_risk_audits(email, limit=12)

    factor_counts: dict[str, int] = {}
    summary = {
        "screened_this_month": usage,
        "estimated_savings_inr": savings,
        "recent_force_prepaid": 0,
        "recent_allow_cod": 0,
        "recent_rto": 0,
        "recent_fraud_confirmed": 0,
    }
    recent_decisions = []

    for row in recent_rows:
        decision = row.get("decision") or "ALLOW_COD"
        outcome = row.get("outcome") or "PENDING"
        if decision == "FORCE_PREPAID":
            summary["recent_force_prepaid"] += 1
        else:
            summary["recent_allow_cod"] += 1
        if outcome == "RTO":
            summary["recent_rto"] += 1
        elif outcome == "FRAUD_CONFIRMED":
            summary["recent_fraud_confirmed"] += 1

        flags = [flag for flag in (row.get("reasons") or "").split(",") if flag]
        for flag in flags:
            factor_counts[flag] = factor_counts.get(flag, 0) + 1

        recent_decisions.append({
            "risk_id": row.get("risk_id"),
            "uid": row.get("uid"),
            "score": round(float(row.get("risk_score") or 0), 1),
            "decision": decision,
            "flags": flags,
            "outcome": outcome,
            "timestamp": row.get("timestamp"),
        })

    top_factors = [
        {"label": label, "count": count}
        for label, count in sorted(factor_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]

    return {
        "summary": summary,
        "recent_audits": recent_rows,
        "last_latency": float(await r.get(f"stats:latency:{email}") or 0),
        "top_flags": sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    }

@router.get("/auth/settings", summary="Get merchant account settings")
async def auth_settings(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "email": email,
        "settings": {
            "company_name": user_data.get("company_name", ""),
            "category": user_data.get("category", ""),
            "monthly_orders": user_data.get("monthly_orders", ""),
            "cod_share": user_data.get("cod_share", ""),
        },
    }

@router.post("/auth/settings", summary="Update merchant account settings")
async def update_auth_settings(update: MerchantSettingsUpdate, request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_key = f"user:{email}"
    user_data = await r.hgetall(user_key)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    fields = {}
    if update.company_name is not None:
        fields["company_name"] = update.company_name.strip()
    if update.category is not None:
        fields["category"] = update.category.strip()
    if update.monthly_orders is not None:
        fields["monthly_orders"] = update.monthly_orders.strip()
    if update.cod_share is not None:
        fields["cod_share"] = update.cod_share.strip()

    if fields:
        await r.hset(user_key, mapping=fields)

    return {
        "status": "success",
        "settings": {
            "company_name": fields.get("company_name", user_data.get("company_name", "")),
            "category": fields.get("category", user_data.get("category", "")),
            "monthly_orders": fields.get("monthly_orders", user_data.get("monthly_orders", "")),
            "cod_share": fields.get("cod_share", user_data.get("cod_share", "")),
        },
    }

@router.get("/auth/settings/webhooks", summary="Get merchant webhook settings")
async def get_webhook_settings(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "email": email,
        "webhook_url": user_data.get("alert_webhook_url", ""),
        # Never return the secret itself for security
        "has_secret": bool(user_data.get("webhook_secret"))
    }

@router.post("/auth/settings/webhooks", summary="Update merchant webhook settings")
async def update_webhook_settings(update: WebhookSettingsUpdate, request: Request, _csrf = Depends(require_csrf)):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_key = f"user:{email}"
    fields = {}
    if update.alert_webhook_url is not None:
        fields["alert_webhook_url"] = update.alert_webhook_url.strip()
    if update.webhook_secret is not None:
        fields["webhook_secret"] = update.webhook_secret.strip()

    if fields:
        await r.hset(user_key, mapping=fields)

    return {"status": "success", "webhook_url": fields.get("alert_webhook_url", "")}

@router.post("/auth/upgrade-request", summary="Request a paid plan upgrade")
async def request_upgrade(req: UpgradeRequest, request: Request, _csrf = Depends(require_csrf)):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    payload = {
        "email": email,
        "current_plan": user_data.get("plan", "free"),
        "requested_plan": req.requested_plan,
        "note": (req.note or "").strip(),
        "status": "submitted",
        "submitted_at": str(time.time()),
    }
    await r.hset(f"upgrade_request:{email}", mapping=payload)
    await r.sadd("upgrade_request_emails", email)
    _log_event(
        "upgrade_request_created",
        email=email,
        current_plan=payload["current_plan"],
        requested_plan=req.requested_plan,
    )
    return {"status": "success", "request": payload}

@router.get("/auth/upgrade-request", summary="Get the current merchant upgrade request")
async def get_upgrade_request(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    payload = await r.hgetall(f"upgrade_request:{email}")
    return {"request": payload or None}

@router.get("/auth/rules", summary="Get merchant automation rules")
async def get_rules(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")
    
    rules = await engine.get_rules(email)
    return {"rules": rules}

@router.post("/auth/rules", summary="Update merchant automation rules")
async def update_rules(update: AutomationRulesUpdate, request: Request, _csrf = Depends(require_csrf)):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Convert Pydantic models to dicts for storage
    rules_dict = [r.model_dump() for r in update.rules]
    await engine.save_rules(email, rules_dict)
    return {"status": "success", "rules": rules_dict}

@router.get("/auth/actions/history", summary="Get merchant action history")
async def get_action_history(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")
    
    history = await engine.get_action_history(email)
    return {"history": history}

@router.post("/order-delivered", summary="Mark order as delivered — builds user trust")
async def mark_delivered(uid: str, merchant: dict = Depends(require_api_key)):
    try:
        merchant_key_hash = merchant["key_hash"]
        async with r.pipeline() as pipe:
            pipe.incr(f"repdelivered:{merchant_key_hash}:{uid}")
            pipe.incr(f"reptotal:{merchant_key_hash}:{uid}")
            await pipe.execute()
        return {"uid": uid, "status": "updated"}
    except Exception as e:
        logging.error(f"Failed to update delivery rep: {e}")
        return {"uid": uid, "status": "failed", "reason": str(e)}

@router.get("/merchant/stats", summary="Merchant: Fetch usage and block stats")
async def get_merchant_stats(merchant: dict = Depends(require_api_key)):
    # ... (Implementation from previous stats)
    key_hash = merchant["key_hash"]
    email = merchant["email"]
    usage = int(await r.get(f"usage:{key_hash}:{time.strftime('%Y-%m')}") or 0)
    total_blocks = int(await r.get(f"stats:blocks:{key_hash}") or 0)
    total_savings = int(await r.get(f"stats:savings:{key_hash}") or 0)
    
    return {
        "email": email,
        "usage_this_month": usage,
        "plan": merchant["data"].get("plan", "starter"),
        "total_blocks": total_blocks,
        "total_savings_inr": total_savings,
        "recent_activity": await AUDIT_STORE.fetch_recent_risk_audits(email, limit=5)
    }

@router.get("/merchant/config", summary="Merchant: Fetch current risk profile weights")
async def get_merchant_config(merchant: dict = Depends(require_api_key)):
    return {
        "email": merchant["email"],
        "risk_config": await _resolve_risk_config(merchant["data"]),
        "is_custom": _has_custom_risk_profile(merchant["data"])
    }

@router.post("/auth/config", summary="Update merchant risk threshold weights", dependencies=[Depends(require_csrf), Depends(role_required(["ADMIN"]))])
async def update_risk_config(req: RiskConfigUpdateRequest, request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    email = await r.get(f"session:{session_id}")
    if not email: raise HTTPException(status_code=401)

    user_data = await r.hgetall(f"user:{email}")
    if not user_data: raise HTTPException(status_code=404, detail="User not found")

    key_hash = user_data.get("api_key_hash") # Assuming api_key_hash is stored in user data
    if not key_hash: raise HTTPException(status_code=400, detail="API key hash not found for user.")

    profile = user_data # Use user_data as the profile for _resolve_risk_config
    previous_config = await _resolve_risk_config(profile)
    payload = req.model_dump(exclude_none=True)
    updates = {}
    for name, value in payload.items():
        coerced = _validate_risk_value(name, _coerce_risk_value(name, value))
        updates[f"risk_{name}"] = str(coerced)
    if updates:
        await r.hset(f"user:{email}", mapping=updates) # Update user data directly
    new_profile = await r.hgetall(f"user:{email}")
    new_config = await _resolve_risk_config(new_profile)
    await _log_risk_profile_change(email, f"merchant:{email}", "UPDATE", previous_config, new_config)
    return {"email": email, "risk_config": new_config, "is_custom": _has_custom_risk_profile(new_profile)}

@router.post("/auth/test-connection", summary="SDK: Test API key connectivity")
async def test_connection(merchant: dict = Depends(require_api_key)):
    return {"status": "success", "authenticated_as": merchant["email"]}

@router.post("/auth/financial-shield/opt-in", summary="Opt-in to RTO Insurance pilot")
async def financial_shield_opt_in(request: Request, _csrf = Depends(require_csrf)):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    email = await r.get(f"session:{session_id}")
    if not email: raise HTTPException(status_code=401)
    
    await r.set(f"merchant:shield:active:{email}", "true")
    await _log_event(email, "FINANCIAL_SHIELD_OPT_IN", {"status": "active"})
    return {"status": "success", "shield_active": True}

@router.get("/auth/financial-shield/stats", summary="Get insurance coverage stats")
async def financial_shield_stats(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    email = await r.get(f"session:{session_id}")
    if not email: raise HTTPException(status_code=401)
    
    is_active = await r.get(f"merchant:shield:active:{email}")
    # Simulate coverage data
    return {
        "is_active": is_active == "true",
        "shielded_capital": 450000 if is_active == "true" else 0,
        "active_claims": 0,
        "premium_accrued": 1250 if is_active == "true" else 0
    }

from app.services.dispute_service import dispute_service

@router.get("/auth/dispute/{risk_id}/evidence", summary="Get forensic evidence bundle for a dispute")
async def get_dispute_evidence(risk_id: str, request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    
    # Ownership check
    email = await r.get(f"session:{session_id}")
    audit = await AUDIT_STORE.get_audit_by_id(risk_id)
    if not audit or audit.get("email") != email:
        raise HTTPException(status_code=403, detail="Evidence not authorized for this identity.")

    evidence = await dispute_service.generate_evidence_bundle(risk_id)
    return evidence

@router.get("/auth/disputes", summary="Get all merchant disputes")
async def get_my_disputes(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    email = await r.get(f"session:{session_id}")
    
    disputes = await dispute_service.get_merchant_disputes(email)
    return {"disputes": disputes}
from app.services.autopilot_service import autopilot_service

@router.get("/auth/autopilot/suggestion", summary="Get AI policy optimization suggestion")
async def get_autopilot_suggestion(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    email = await r.get(f"session:{session_id}")
    
    suggestion = await autopilot_service.get_optimization_suggestion(email)
    return suggestion

@router.post("/auth/autopilot/apply", summary="Apply AI-suggested policy optimization", dependencies=[Depends(require_csrf), Depends(role_required(["ADMIN"]))])
async def apply_autopilot_optimization(request: Request, config_patch: dict):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    email = await r.get(f"session:{session_id}")
    
    if not config_patch:
        raise HTTPException(status_code=400, detail="No optimization patch provided.")
        
    success = await autopilot_service.apply_optimization(email, config_patch)
    return {"status": "SUCCESS" if success else "FAILED"}

from app.services.identity_linker import identity_linker

@router.get("/auth/identity/graph/{id_type}/{id_val}", summary="Get identity connection graph")
async def get_identity_connection_graph(id_type: str, id_val: str, request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    
    graph = await identity_linker.get_identity_graph(id_type, id_val)
    return {"graph": graph}@router.get("/auth/team/members", summary="List enterprise team members")
async def get_team_members(request: Request, role: str = Depends(get_current_user_role)):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    email = await r.get(f"session:{session_id}")
    
    # In this simplified model, "team" is defined by users who share the same domain or were explicitly linked.
    # For now, we'll return a mock list based on the user's domain for demo purposes.
    domain = email.split("@")[-1]
    
    # We'll search for users in Redis with this domain (this is a simplified proxy for a team_id)
    all_users = await r.keys("user:*")
    team_members = []
    for u_key in all_users:
        u_email = u_key.split(":")[-1]
        if u_email.endswith(f"@{domain}"):
            u_data = await r.hgetall(u_key)
            team_members.append({
                "email": u_email,
                "role": u_data.get("role", "ANALYST"),
                "status": "ACTIVE"
            })
    
    return {"team_name": domain.split(".")[0].upper(), "members": team_members}

@router.post("/auth/team/members", summary="Invite/Add a member to the enterprise team", dependencies=[Depends(role_required(["ADMIN"]))])
async def add_team_member(payload: dict, request: Request):
    new_email = payload.get("email")
    new_role = payload.get("role", "ANALYST")
    
    if not new_email:
        raise HTTPException(status_code=400, detail="Member email is required.")
        
    # Check if user already exists
    if await r.exists(f"user:{new_email}"):
        # Update role if they exist
        await r.hset(f"user:{new_email}", "role", new_role)
    else:
        # Create a skeleton user (they will need to set password later, but for now they can be added)
        await r.hset(f"user:{new_email}", mapping={
            "role": new_role,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "plan": "enterprise_child"
        })
        
    _log_event("team_member_added", email=new_email, role=new_role)
    return {"status": "success", "message": f"Member {new_email} added as {new_role}"}

@router.get("/auth/telemetry/live", summary="Get live global attack telemetry")
async def get_live_telemetry(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id: raise HTTPException(status_code=401)
    
    # Retrieve last 500 events
    events_raw = await r.lrange("global:telemetry:geo", 0, 499)
    events = [json.loads(e) for e in events_raw]
    return {"events": events}
