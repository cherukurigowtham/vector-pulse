import json
import logging
from typing import Dict, Any, List
from app.core.redis import r
from app.services.simulation_service import simulation_service
from app.db.database import AUDIT_STORE

logger = logging.getLogger(__name__)

class AutoPilotService:
    """
    Phase 22: Intelligent Auto-Pilot.
    Autonomous policy generation and optimization.
    """

    async def get_optimization_suggestion(self, email: str) -> Dict[str, Any]:
        """
        Analyzes recent delivery outcomes and proposes config adjustments.
        It uses 'Outcome Drift' detection: Rising RTO despite high block rates.
        """
        audits = await AUDIT_STORE.fetch_all_merchant_audits(email, limit=200)
        if not audits:
            return {"status": "INSUFFICIENT_DATA", "message": "Need more historical traffic to calibrate Auto-Pilot."}

        # 1. Analyze Outcome Drift
        total = len(audits)
        rto_count = sum(1 for a in audits if a.get("outcome") == "RTO")
        fraud_count = sum(1 for a in audits if a.get("outcome") == "FRAUD_CONFIRMED")
        
        rto_rate = (rto_count / total) * 100 if total > 0 else 0
        
        # Threshold for 'Drift' detection: RTO rate higher than 5%
        if rto_rate < 5.0:
            return {
                "status": "OPTIMIZED",
                "message": f"Policy is performing well. Current RTO rate: {rto_rate:.1f}%",
                "suggestion": None
            }

        logger.info(f"Outcome Drift Detected for {email}: RTO Rate {rto_rate:.1f}%")

        # 2. Identify the weakest signal in RTO cases
        # We look for risk factors that were FALSE in RTO orders but should have been TRUE
        weak_signals = {}
        for audit in audits:
            if audit.get("outcome") in ["RTO", "FRAUD_CONFIRMED"]:
                try:
                    metrics = json.loads(audit["metrics"])
                    # Check which indicators were low but are typically high-risk
                    if not metrics.get("vpn", False): weak_signals["vpn_weight"] = weak_signals.get("vpn_weight", 0) + 1
                    if not metrics.get("global_network", False): weak_signals["global_network_weight"] = weak_signals.get("global_network_weight", 0) + 1
                    if not metrics.get("device_velocity", False): weak_signals["device_velocity_weight"] = weak_signals.get("device_velocity_weight", 0) + 1
                except:
                    continue

        if not weak_signals:
            return {"status": "STABLE", "message": "No clear optimization vector identified.", "suggestion": None}

        # Pick the most common weak signal
        best_factor = max(weak_signals, key=weak_signals.get)
        
        # 3. Simulate Improvement
        # We'll try boosting this factor by 20%
        candidate_config = {best_factor: 25.0} # Fixed boost for simulation
        sim_results = await simulation_service.run_simulation(email, candidate_config, limit=100)
        
        return {
            "status": "IMPROVEMENT_AVAILABLE",
            "message": f"Detected RTO drift ({rto_rate:.1f}%). Recommending adjustment to {best_factor}.",
            "suggestion": {
                "factor": best_factor,
                "adjustment": 25.0,
                "reason": f"Boosting {best_factor.replace('_', ' ')} could have prevented high-risk RTOs in recent history.",
                "expected_impact": {
                    "new_blocks": sim_results.get("new_blocks", 0),
                    "new_approvals": sim_results.get("new_approvals", 0)
                },
                "candidate_config": candidate_config
            }
        }

    async def apply_optimization(self, email: str, config_patch: Dict[str, Any]):
        """Applies the suggested config patch directly to the merchant's live settings."""
        current_raw = await r.get(f"config:{email}")
        if not current_raw:
            from app.core.config import RISK_CONFIG
            current = RISK_CONFIG.copy()
        else:
            current = json.loads(current_raw)
            
        current.update(config_patch)
        await r.set(f"config:{email}", json.dumps(current))
        await r.expire(f"config:{email}", 86400 * 30)
        return True

autopilot_service = AutoPilotService()
