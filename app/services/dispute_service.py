import logging
import json
from typing import Dict, Any, Optional
from app.db.database import AUDIT_STORE
from app.core.redis import r

logger = logging.getLogger(__name__)

class DisputeService:
    """
    Phase 20: Advanced Dispute Management & Chargeback Shield.
    Generates automated evidence packages for merchants to defend against chargebacks.
    """

    async def generate_evidence_bundle(self, risk_id: str) -> Dict[str, Any]:
        """
        Aggregates forensic signals into a standardized evidence package.
        """
        audit = await AUDIT_STORE.get_audit_by_id(risk_id)
        if not audit:
            return {"error": "Audit record not found."}

        # Parse metrics
        try:
            metrics = json.loads(audit.get("metrics", "{}"))
        except:
            metrics = {}

        # 1. Identity & Network Signal Evidence
        network_evidence = {
            "ip_address": metrics.get("ip", "Unknown"),
            "geo_location": metrics.get("geo_info", "Unknown"),
            "network_reputation": "HIGH_TRUST" if not metrics.get("global_network", False) else "SUSPICIOUS",
            "consortium_hits": metrics.get("consortium_hits", 0),
            "is_vpn_proxy": metrics.get("vpn", False),
            "device_fingerprint_match": metrics.get("device_match", True)
        }

        # 2. Behavioral DNA Evidence (Hardest to fakes)
        behavioral_evidence = {
            "mouse_entropy": metrics.get("mouse_entropy", 0.0),
            "keystroke_velocity": metrics.get("keystroke_velocity", 0.0),
            "time_on_page_secs": metrics.get("session_duration", 0),
            "bot_speed_detected": metrics.get("bot_speed", False),
            "behavioral_match": "CONSISTENT" if metrics.get("trust", 50) > 40 else "ANOMALOUS"
        }

        # 3. Decision Narrative
        evidence_bundle = {
            "vantix_risk_id": risk_id,
            "order_id": audit.get("uid", "N/A"),
            "timestamp": audit.get("timestamp"),
            "risk_score_at_time_of_purchase": audit.get("risk_score"),
            "final_decision": audit.get("decision"),
            "evidence_signals": {
                "network_layer": network_evidence,
                "behavioral_layer": behavioral_evidence
            },
            "adjudication_narrative": audit.get("reasons", "No specific flags triggered.")
        }

        return evidence_bundle

    async def mark_dispute_status(self, risk_id: str, status: str):
        """
        Status should be one of: 'CHARGEBACK', 'DISPUTE_OPEN', 'DISPUTE_WON', 'DISPUTE_LOST'
        """
        # Store in Redis for quick access in dashboard
        # Format: dispute:merchant_email -> list of risk_ids
        audit = await AUDIT_STORE.get_audit_by_id(risk_id)
        if audit:
            email = audit.get("email")
            await r.hset(f"disputes:{email}", risk_id, status)
            # Also update outcome in DB
            await AUDIT_STORE.update_audit_outcome(risk_id, status)
        
    async def get_merchant_disputes(self, email: str) -> Dict[str, str]:
        return await r.hgetall(f"disputes:{email}")

dispute_service = DisputeService()
