import time
import json
import hashlib
import secrets
import logging
import asyncio
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Security,
    BackgroundTasks,
    Response,
)
from app.models import Order, OutcomeUpdate

logger = logging.getLogger(__name__)
from app.core.config import RISK_CONFIG, RISK_FAIL_CLOSED, RATE_LIMITS
from app.core.redis import r
from app.db.database import AUDIT_STORE
from app.core.security import require_api_key, require_api_key_or_admin
from app.core.helpers import (
    _key_preview,
    _resolve_risk_config,
    _sliding_window_rate_limit,
    _log_event,
)
from app.services.risk_service import run_risk_analysis, _merchant_state_key
from app.services.cache_service import dfc
from app.core.intelligence import get_cluster_risk_bonus, apply_outcome_feedback
from app.services.graph_service import link_identity
from app.services.quarantine_service import process_fraud_feedback
from app.services.monitoring_service import track_decision_bias

router = APIRouter(tags=["risk"])


async def _perform_post_analysis_ops(
    order: Order,
    analysis: dict,
    risk_id: str,
    action: str,
    risk_config: dict,
    merchant_key_hash: str,
    merchant_email: str,
    usage_key: str,
    team_id: str | None = None,
):
    try:
        context = {
            "uid": order.uid,
            "score": float(analysis["score"]),
            "flags": analysis["flags"],
            "metrics": analysis["metrics"],
            "xai_impacts": analysis.get("xai_impacts", {}),
            "timestamp": time.time(),
            "config": risk_config,
            "identities": {
                "email": order.email,
                "phone": order.phone,
                "addr": order.addr,
            },
        }
        await AUDIT_STORE.insert_risk_audit(
            {
                "risk_id": risk_id,
                "uid": order.uid,
                "email": merchant_email,
                "team_id": team_id,
                "risk_score": float(analysis["score"]),
                "decision": action,
                "shadow_mode": 1 if order.shadow else 0,
                "reasons": ",".join(analysis["flags"]),
                "metrics": json.dumps(analysis["metrics"]),
                "timestamp": time.time(),
            }
        )

        # Update usage and explain context individually for stability
        await r.incr(usage_key)
        await r.expire(usage_key, 86400 * 60)
        await r.setex(f"explain:{risk_id}", 86400 * 3, json.dumps(context))
        await r.sadd(f"user_uids:{merchant_email}", order.uid)
        await r.expire(f"user_uids:{merchant_email}", 86400 * 90)

        if analysis["score"] > risk_config["decision_threshold"]:
            await r.incrby("total_savings_inr", risk_config["savings_per_block_inr"])
            await r.expire("total_savings_inr", 86400 * 365)

            savings_key = f"stats:savings:{merchant_key_hash}"
            blocks_key = f"stats:blocks:{merchant_key_hash}"
            await r.incrby(savings_key, risk_config["savings_per_block_inr"])
            await r.expire(savings_key, 86400 * 90)
            awards_key = f"stats:awards:{merchant_key_hash}"
            await r.incr(awards_key)
            await r.expire(awards_key, 86400 * 90)

        # 3. Distributed Fraud Cache (DFC) Proactive Sync
        await dfc.update_cache(
            order.email,
            merchant_email,
            {
                "score": analysis["score"],
                "decision": action,
                "flags": analysis["flags"],
                "timestamp": context["timestamp"],
                "risk_id": risk_id,
            },
        )

        await r.expire(blocks_key, 86400 * 90)

        status_label = "SHADOW_BLOCK" if order.shadow else "BLOCK"
        await r.lpush(
            "recent_blocks",
            f"{order.uid}: {', '.join(analysis['flags'])} ({status_label}: {analysis['score']:.0f}) [ID: {risk_id}]",
        )
        await r.ltrim("recent_blocks", 0, 49)
        await r.expire("recent_blocks", 86400 * 7)

        m = analysis["metrics"]
        if m.get("velocity"):
            await r.incr("stat:velocity")
        if m.get("sybil"):
            await r.incr("stat:sybil")
        if m.get("price"):
            await r.incr("stat:price")

        if (
            m.get("anomaly_flag")
            or m.get("is_cluster_flag")
            or "IDENTITY_CLUSTER_DETECTED" in analysis["flags"]
        ):
            await r.incr("stat:clusters")
        if (
            m.get("vpn")
            or m.get("geo_velocity")
            or "IMPOSSIBLE_TRAVEL" in analysis["flags"]
            or "ANONYMOUS_IP_DETECTED" in analysis["flags"]
        ):
            await r.incr("stat:geoip")

        await r.incr("total_blocks")

        state_key = _merchant_state_key(merchant_key_hash, "reptotal", order.uid)
        await r.incr(state_key)
        await r.expire(state_key, 86400 * 30)
        await r.expire(f"risk_index:{merchant_email}", 86400 * 90)

        # Pillar 3 (v4): Bias Monitoring
        await track_decision_bias(
            merchant_email, action, {"bin_prefix": order.uid[:6], "geo_code": "IN"}
        )
    except Exception as e:
        logging.warning(f"Post-analysis operations failed: {e}")


@router.get(
    "/v1/explain/{risk_id}", summary="Get human-readable reasoning for a fraud decision"
)
async def explain_decision(
    risk_id: str, key_data: dict = Depends(require_api_key_or_admin)
):
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
                "metrics": payload.get("metrics", payload)
                if isinstance(payload, dict)
                else payload,
                "config": payload.get("config", dict(RISK_CONFIG))
                if isinstance(payload, dict)
                else dict(RISK_CONFIG),
                "timestamp": row["timestamp"],
            }
        else:
            context = json.loads(raw_data)

        narrative = []
        m = context["metrics"]
        config = context.get("config", dict(RISK_CONFIG))
        if m.get("velocity"):
            narrative.append(
                f"High-frequency transaction wave detected ({config['velocity_max_orders']}+ orders in {config['velocity_window_secs']}s)."
            )
        if m.get("vpn"):
            narrative.append(
                "Anonymous networking footprint identified (VPN/Proxy detected)."
            )
        if m.get("price"):
            narrative.append(
                "Transaction value represents a significant statistical outlier compared to user history."
            )
        if m.get("sybil"):
            narrative.append(
                "Sybil identity pattern detected: multiple unique identifiers linked to a single delivery location."
            )
        if m.get("trust", 50.0) < config["trust_floor"]:
            narrative.append(
                f"Customer reputation score ({m['trust']:.0f}%) is below the merchant's delivery safety floor."
            )

        return {
            "risk_id": risk_id,
            "score": context["score"],
            "decision": (
                "FORCE_PREPAID"
                if context["score"] > config["decision_threshold"]
                else "ALLOW_COD"
            ),
            "findings": narrative,
            "impact_analysis": context.get("xai_impacts", {}),  # Professional XAI
            "raw_metrics": m,
            "timestamp": context["timestamp"],
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logging.error(f"Explain API Error: {e}")
        raise HTTPException(status_code=500, detail="Internal analysis service error")


@router.post("/v1/risk-check", summary="Evaluate an order for fraud risk")
async def check_order(
    order: Order, bg: BackgroundTasks, key_data: dict = Depends(require_api_key)
):
    start_time = time.perf_counter()
    risk_config = await _resolve_risk_config(key_data)
    merchant_key_hash = key_data.get("key_hash")
    merchant_email = key_data.get("email")
    plan = key_data.get("data", {}).get("plan", "free")

    # 0. Distributed Fraud Cache (DFC) Sub-10ms Lookup
    cached = await dfc.get_decision(order.email, merchant_email)
    if cached:
        # Check if cache is still valid for this merchant's current threshold
        if cached.get("score", 0) < risk_config.get("decision_threshold", 50):
            logger.info(f"DFC HIT | Fast-tracking order {order.uid} for {order.email}")
            return Response(
                content=json.dumps(cached),
                media_type="application/json",
                headers={"X-Vantix-Cache": "HIT", "X-Latency-MS": "0"},
            )

    # Ratelimit
    if await _sliding_window_rate_limit(f"burst:{merchant_key_hash}", 50, 1):
        raise HTTPException(status_code=429, detail="Burst rate limit exceeded.")

    # Quota
    current_month = time.strftime("%Y-%m")
    usage_key = f"usage:{merchant_key_hash}:{current_month}"
    usage = int(await r.get(usage_key) or 0)
    limit = RATE_LIMITS.get(plan, 1000)
    if usage >= limit:
        raise HTTPException(status_code=402, detail="Quota exceeded.")

    try:
        analysis = await asyncio.wait_for(
            run_risk_analysis(order, risk_config, merchant_key_hash, merchant_email),
            timeout=0.6,
        )
    except (asyncio.TimeoutError, Exception) as e:
        error_type = (
            "TIMEOUT" if isinstance(e, asyncio.TimeoutError) else "ENGINE_ERROR"
        )
        logging.error(f"Analysis Failed ({error_type}) [Order: {order.uid}]: {str(e)}")
        risk_score = 100.0 if RISK_FAIL_CLOSED else 0.0
        analysis = {
            "score": risk_score,
            "flags": [f"{error_type}_FALLBACK"],
            "metrics": {},
            "trust_score": 50.0,
        }

    # Semantic ML Cluster Bonus
    try:
        cluster_bonus = await get_cluster_risk_bonus(order)
    except Exception:
        cluster_bonus = 0.0
    if cluster_bonus > 0:
        analysis["score"] += cluster_bonus
        analysis["flags"].append("FRAUD_RING_CLUSTER_DETECTED")

    risk_score = analysis["score"]
    is_blocked = (risk_score > risk_config["decision_threshold"]) and not order.shadow
    action = "FORCE_PREPAID" if is_blocked else "ALLOW_COD"
    risk_id = secrets.token_hex(8)

    bg.add_task(
        _perform_post_analysis_ops,
        order,
        analysis,
        risk_id,
        action,
        risk_config,
        merchant_key_hash,
        merchant_email,
        usage_key,
        key_data.get("team_id"),
    )

    latency = (time.perf_counter() - start_time) * 1000
    bg.add_task(r.set, f"stats:latency:{merchant_email}", str(latency))

    return {
        "uid": order.uid,
        "risk_id": risk_id,
        "decision": action,
        "shadow_mode": order.shadow,
        "risk_score": round(float(risk_score), 1),
        "risk_factors": analysis["flags"],
        "latency_ms": f"{latency:.2f}ms",
    }


async def _handle_outcome_feedback(risk_id: str, status: str, merchant_email: str):
    """
    Consolidated ML Feedback entry point.
    """
    try:
        raw_context = await r.get(f"explain:{risk_id}")
        if not raw_context:
            return
        context = json.loads(raw_context)
        flags = context.get("flags", [])
        identities = context.get("identities", {})

        # Call the core neural engine in intelligence
        await apply_outcome_feedback(
            merchant_email, flags, status, identities=identities
        )
    except Exception as e:
        logging.warning(f"Feedback processing failed for {risk_id}: {e}")


@router.post(
    "/v1/outcome",
    summary="Report the final outcome of a transaction (ML Feedback Loop)",
)
async def update_outcome(
    update: OutcomeUpdate,
    bg: BackgroundTasks,
    key_data: dict = Depends(require_api_key),
):
    try:
        await AUDIT_STORE.update_outcome(
            update.risk_id, update.status, reason=update.reason
        )
        # Pillar 1 & 2: Autonomous Intelligence Loop
        merchant_email = key_data.get("email")
        bg.add_task(
            _handle_outcome_feedback, update.risk_id, update.status, merchant_email
        )

        if update.status == "FRAUD_CONFIRMED":
            # Extract order_hash from the explain context if possible
            raw_context = await r.get(f"explain:{update.risk_id}")
            if raw_context:
                context = json.loads(raw_context)
                order_hash = context.get("metrics", {}).get("order_hash")
                if order_hash:
                    bg.add_task(process_fraud_feedback, order_hash, merchant_email)

        _log_event(
            "outcome_updated",
            risk_id=update.risk_id,
            status=update.status,
            merchant=merchant_email,
        )
        return {
            "status": "success",
            "risk_id": update.risk_id,
            "updated_to": update.status,
        }
    except Exception as e:
        logging.error(f"Outcome update failed for {update.risk_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Internal persistence error. Please retry."
        )
