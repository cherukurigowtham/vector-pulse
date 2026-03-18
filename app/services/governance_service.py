import logging
from typing import Dict, Any
from app.core.redis import r
from app.core.config import RISK_CONFIG

logger = logging.getLogger(__name__)

class GovernanceService:
    """
    Autonomous Governance engine (Phase 29).
    Implements a feedback loop to dynamically adjust risk weights 
    based on merchant accuracy signals.
    """

    async def get_adjusted_weights(self, merchant_email: str) -> Dict[str, float]:
        """
        Retrieves the dynamically tuned weights for a specific merchant.
        Fallback to global RISK_CONFIG if no tuning data exists.
        """
        tuned_key = f"governance:weights:{merchant_email}"
        tuned_data = await r.hgetall(tuned_key)
        
        weights = {
            "velocity_weight": float(tuned_data.get("velocity_weight", RISK_CONFIG["velocity_weight"])),
            "sybil_weight": float(tuned_data.get("sybil_weight", RISK_CONFIG["sybil_weight"])),
            "anomaly_weight": float(tuned_data.get("anomaly_weight", RISK_CONFIG["anomaly_weight"])),
            "bot_speed_weight": float(tuned_data.get("bot_speed_weight", RISK_CONFIG["bot_speed_weight"])),
            "global_network_weight": float(tuned_data.get("global_network_weight", RISK_CONFIG["global_network_weight"]))
        }
        
        return weights

    async def record_feedback(self, merchant_email: str, risk_id: str, feedback_type: str):
        """
        Records feedback (e.g., FALSE_POSITIVE) and adjusts weights.
        Simulates an RL-style reward/penalty system.
        """
        # feedback_type: "FALSE_POSITIVE", "TRUE_POSITIVE"
        if feedback_type == "FALSE_POSITIVE":
            # Identify which signals fired and penalize their weights
            tuned_key = f"governance:weights:{merchant_email}"
            
            # Ensure we start from current tuned weight or global default
            current_bot_weight = await r.hget(tuned_key, "bot_speed_weight")
            if current_bot_weight is None:
                current_bot_weight = RISK_CONFIG["bot_speed_weight"]
            
            current_vel_weight = await r.hget(tuned_key, "velocity_weight")
            if current_vel_weight is None:
                current_vel_weight = RISK_CONFIG["velocity_weight"]

            async with r.pipeline() as pipe:
                pipe.hset(tuned_key, "bot_speed_weight", float(current_bot_weight) - 1.5)
                pipe.hset(tuned_key, "velocity_weight", float(current_vel_weight) - 1.0)
                await pipe.execute()
                
            logger.info(f"Governance: Penalized weights for {merchant_email} due to FALSE_POSITIVE on {risk_id}")

governance_service = GovernanceService()
