import time
import json
import hashlib
import secrets
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Security, BackgroundTasks
from app.models import Order, OutcomeUpdate
from app.core.config import RISK_CONFIG, RISK_FAIL_CLOSED, RATE_LIMITS
from app.core.redis import r
from app.db.database import AUDIT_STORE
from app.core.security import require_api_key, require_api_key_or_admin
from app.core.helpers import _key_preview, _resolve_risk_config, _sliding_window_rate_limit, _log_event
from app.services.risk_service import run_risk_analysis, _merchant_state_key
from app.services.graph_service import link_identity
from app.services.quarantine_service import process_fraud_feedback

router = APIRouter(tags=["risk"])

async def _perform_post_analysis_ops(
    order: Order,
    analysis: dict,
    risk_id: str,
    action: str,
    risk_config: dict,
    merchant_key_hash: str,
    merchant_email: str,
    usage_key: str
):
    try:
        context = {
            "uid": order.uid,
            "score": float(analysis["score"]),
            "flags": analysis["flags"],
            "metrics": analysis["metrics"],
            "timestamp": time.time(),
            "config": risk_config
        }
        await AUDIT_STORE.insert_risk_audit({
            "risk_id": risk_id,
            "uid": order.uid,
            "email": merchant_email,
            "risk_score": float(analysis["score"]),
            "decision": action,
            "shadow_mode": 1 if order.shadow else 0,
            "reasons": ",".join(analysis["flags"]),
            "metrics": json.dumps(analysis["metrics"]),
            "timestamp": time.time()
        })

        async with r.pipeline() as pipe:
            pipe.incr(usage_key)
            pipe.expire(usage_key, 86400 * 60)
            pipe.setex(f"explain:{risk_id}", 86400 * 3, json.dumps(context))
            pipe.sadd(f"user_uids:{merchant_email}", order.uid)
            pipe.expire(f"user_uids:{merchant_email}", 86400 * 90)
            
            if analysis["score"] > risk_config["decision_threshold"]:
                pipe.incrby("total_savings_inr", risk_config["savings_per_block_inr"])
                pipe.expire("total_savings_inr", 86400 * 365)
                
                savings_key = f"stats:savings:{merchant_key_hash}"
                blocks_key = f"stats:blocks:{merchant_key_hash}"
                pipe.incrby(savings_key, risk_config["savings_per_block_inr"])
                pipe.expire(savings_key, 86400 * 90)
                pipe.incr(blocks_key)
                pipe.expire(blocks_key, 86400 * 90)
                
                status_label = "SHADOW_BLOCK" if order.shadow else "BLOCK"
                pipe.lpush("recent_blocks", f"{order.uid}: {', '.join(analysis['flags'])} ({status_label}: {analysis['score']:.0f}) [ID: {risk_id}]")
                pipe.ltrim("recent_blocks", 0, 49)
                pipe.expire("recent_blocks", 86400 * 7)

                m = analysis["metrics"]
                if m.get("velocity"): pipe.incr("stat:velocity")
                if m.get("sybil"):    pipe.incr("stat:sybil")
                if m.get("price"):    pipe.incr("stat:price")
                if m.get("anomaly_flag") or m.get("is_cluster_flag") or "IDENTITY_CLUSTER_DETECTED" in analysis["flags"]:
                    pipe.incr("stat:clusters")
                if m.get("vpn") or m.get("geo_velocity") or "IMPOSSIBLE_TRAVEL" in analysis["flags"] or "ANONYMOUS_IP_DETECTED" in analysis["flags"]:
                    pipe.incr("stat:geoip")
                
                for s in ["stat:velocity", "stat:sybil", "stat:price", "stat:clusters", "stat:geoip", "total_blocks"]:
                    pipe.expire(s, 86400 * 30)
                pipe.incr("total_blocks")
            
            state_key = _merchant_state_key(merchant_key_hash, "reptotal", order.uid)
            pipe.incr(state_key)
            pipe.expire(state_key, 86400 * 30)
            pipe.expire(f"risk_index:{merchant_email}", 86400 * 90)
            await pipe.execute()
    except Exception as e:
        logging.warning(f"Post-analysis operations failed: {e}")

@router.get("/v1/explain/{risk_id}", summary="Get human-readable reasoning for a fraud decision")
async def explain_decision(risk_id: str, key_data: dict = Depends(require_api_key_or_admin)):
    try:
        raw_data = await r.get(f"explain:{risk_id}")
        if not raw_data:
            row = await AUDIT_STORE.fetch_risk_audit(risk_id)
            if not row:
                raise HTTPException(status_code=404, detail="Risk ID not found")
            payload = json.loads(row["metrics"])
            context = {
                "score": row["risk_score"],
                "flags": row["reasons"].split(",") if row["reasons"] else [],
                "metrics": payload.get("metrics", payload) if isinstance(payload, dict) else payload,
                "config": payload.get("config", dict(RISK_CONFIG)) if isinstance(payload, dict) else dict(RISK_CONFIG),
                "timestamp": row["timestamp"]
            }
        else:
            context = json.loads(raw_data)
        
        narrative = []
        m = context["metrics"]
        config = context.get("config", dict(RISK_CONFIG))
        if m.get("velocity"): narrative.append(f"Multiple orders ({config['velocity_max_orders']}+) detected in {config['velocity_window_secs']}s window.")
        if m.get("vpn"):      narrative.append("Transaction attempted via Data Center or Anonymous Proxy (VPN).")
        if m.get("price"):    narrative.append("Transaction amount significantly deviates from historical average.")
        if m.get("sybil"):    narrative.append("Multiple UIDs linked to same delivery address.")
        if m.get("trust", 50.0) < config["trust_floor"]:
            narrative.append(f"Customer has low delivery score ({m['trust']:.0f}% success).")
        
        return {
            "risk_id": risk_id, "score": context["score"],
            "decision": ("FORCE_PREPAID" if context["score"] > config["decision_threshold"] else "ALLOW_COD"),
            "findings": narrative, "raw_metrics": m, "timestamp": context["timestamp"]
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise
        logging.error(f"Explain API Error: {e}")
        raise HTTPException(status_code=500, detail="Internal analysis service error")

@router.post("/v1/risk-check", summary="Evaluate an order for fraud risk")
async def check_order(order: Order, bg: BackgroundTasks, key_data: dict = Depends(require_api_key)):
    start_time = time.perf_counter()
    risk_config = await _resolve_risk_config(key_data)
    merchant_key_hash = key_data.get("key_hash")
    merchant_email = key_data.get("email")
    plan = key_data.get("data", {}).get("plan", "free")
    
    # Ratelimit
    if await _sliding_window_rate_limit(f"burst:{merchant_key_hash}", 50, 1):
        raise HTTPException(status_code=429, detail="Burst rate limit exceeded.")

    # Quota
    current_month = time.strftime('%Y-%m')
    usage_key = f"usage:{merchant_key_hash}:{current_month}"
    usage = int(await r.get(usage_key) or 0)
    limit = RATE_LIMITS.get(plan, 1000)
    if usage >= limit:
        raise HTTPException(status_code=402, detail="Quota exceeded.")
    
    try:
        analysis = await asyncio.wait_for(
            run_risk_analysis(order, risk_config, merchant_key_hash, merchant_email),
            timeout=0.6
        )
    except (asyncio.TimeoutError, Exception) as e:
        error_type = "TIMEOUT" if isinstance(e, asyncio.TimeoutError) else "ENGINE_ERROR"
        logging.error(f"Analysis Failed ({error_type}) [Order: {order.uid}]: {str(e)}")
        risk_score = 100.0 if RISK_FAIL_CLOSED else 0.0
        analysis = {"score": risk_score, "flags": [f"{error_type}_FALLBACK"], "metrics": {}, "trust_score": 50.0}

    risk_score = analysis["score"]
    is_blocked = (risk_score > risk_config["decision_threshold"]) and not order.shadow
    action = "FORCE_PREPAID" if is_blocked else "ALLOW_COD"
    risk_id = secrets.token_hex(8)

    bg.add_task(_perform_post_analysis_ops, order, analysis, risk_id, action, risk_config, merchant_key_hash, merchant_email, usage_key)

    latency = (time.perf_counter() - start_time) * 1000
    return {
        "uid": order.uid, "risk_id": risk_id, "decision": action, "shadow_mode": order.shadow,
        "risk_score": round(float(risk_score), 1), "risk_factors": analysis["flags"], "latency_ms": f"{latency:.2f}ms",
    }

async def _apply_neural_feedback(risk_id: str, status: str, merchant_email: str):
    """
    Advanced Pillar: Neural Weighting Engine. 
    Analyzes the 'explain' context of a risk decision and adjusts merchant-specific biases.
    """
    try:
        raw_context = await r.get(f"explain:{risk_id}")
        if not raw_context:
            return # Context expired or missing
            
        context = json.loads(raw_context)
        flags = context.get("flags", [])
        score = context.get("score", 0)
        
        # Logic: 
        # If DELIVERED but Score was High -> Weights are too AGGRESSIVE (Bias -1)
        # If RTO/FRAUD but Score was Low -> Weights are too LENIENT (Bias +1)
        
        bias_bucket = f"neural:bias:{merchant_email}"
        adjustment = 0
        if status == "DELIVERED" and score > 40: # threshold from config
            adjustment = -0.5 # Subtly decrease weights
        elif status in ["RTO", "FRAUD_CONFIRMED"] and score < 40:
            adjustment = 1.0 # Aggressively increase weights
            
        if adjustment != 0:
            async with r.pipeline() as pipe:
                for flag in flags:
                    # Map flags to config weights (e.g., HIGH_VELOCITY -> velocity)
                    weight_key = flag.lower().replace("_flag", "").replace("_detected", "").replace("high_", "")
                    if weight_key in RISK_CONFIG:
                        pipe.hincrbyfloat(bias_bucket, weight_key, adjustment)
                await pipe.execute()
                pipe.expire(bias_bucket, 86400 * 90)
    except Exception as e:
        logging.warning(f"Neural profiling failed for {risk_id}: {e}")

@router.post("/v1/outcome", summary="Report the final outcome of a transaction (ML Feedback Loop)")
async def update_outcome(update: OutcomeUpdate, bg: BackgroundTasks, key_data: dict = Depends(require_api_key)):
    try:
        await AUDIT_STORE.update_outcome(
            update.risk_id, 
            update.status,
            reason=update.reason
        )
        # Pillar 1 & 2: Autonomous Intelligence Loop
        merchant_email = key_data.get("email")
        bg.add_task(_apply_neural_feedback, update.risk_id, update.status, merchant_email)
        
        if update.status == "FRAUD_CONFIRMED":
            # Extract order_hash from the explain context if possible
            raw_context = await r.get(f"explain:{update.risk_id}")
            if raw_context:
                context = json.loads(raw_context)
                order_hash = context.get("metrics", {}).get("order_hash")
                if order_hash:
                    bg.add_task(process_fraud_feedback, order_hash, merchant_email)
        
        _log_event("outcome_updated", risk_id=update.risk_id, status=update.status, merchant=merchant_email)
        return {"status": "success", "risk_id": update.risk_id, "updated_to": update.status}
    except Exception as e:
        logging.error(f"Outcome update failed for {update.risk_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal persistence error. Please retry.")
