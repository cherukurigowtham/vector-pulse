import json
import logging
from typing import Dict, Any, List
from app.db.database import AUDIT_STORE
from app.core.redis import r

logger = logging.getLogger(__name__)

class SimulationService:
    """
    Phase 19: Fraud Simulation Sandbox.
    Allows merchants to 'replay' historical traffic against new risk weights and thresholds.
    """
    
    async def run_simulation(self, email: str, candidate_config: Dict[str, Any], limit: int = 500) -> Dict[str, Any]:
        """
        Re-evaluates recent audit records using the provided config.
        """
        # Fetch current config as baseline
        current_config_raw = await r.get(f"config:{email}")
        if current_config_raw:
            full_config = json.loads(current_config_raw)
        else:
            # Fallback to a bare minimum or default if possible
            from app.core.config import RISK_CONFIG
            full_config = RISK_CONFIG.copy()
            
        full_config.update(candidate_config)
        
        audits = await AUDIT_STORE.fetch_all_merchant_audits(email, limit=limit)
        if not audits:
            return {"error": "No historical data found for simulation."}

        stats = {
            "total_scanned": len(audits),
            "original_blocks": 0,
            "simulated_blocks": 0,
            "new_blocks": 0,         # Orders that were ALLOWED but would be BLOCKED
            "new_approvals": 0,      # Orders that were BLOCKED but would be ALLOWED
            "avg_score_original": 0.0,
            "avg_score_simulated": 0.0,
            "threshold_used": candidate_config.get("decision_threshold", 50)
        }

        # Import calculation logic dynamically to avoid circular dependencies
        from app.services.risk_service import _calculate_risk_score
        
        total_orig_score = 0.0
        total_sim_score = 0.0
        
        for audit in audits:
            try:
                metrics = json.loads(audit["metrics"])
            except Exception:
                continue

            orig_score = audit["risk_score"]
            orig_decision = audit["decision"]
            
            if orig_decision == "FORCE_PREPAID":
                stats["original_blocks"] += 1
            
            total_orig_score += orig_score

            # Re-run cognitive score calculation with candidate parameters
            sim_score, _sim_impacts = _calculate_risk_score(
                metrics.get("velocity", False),
                metrics.get("sybil", False),
                metrics.get("price", False),
                metrics.get("identity", False),
                metrics.get("is_cluster_flag", False),
                metrics.get("trust", 50.0),
                metrics.get("vpn", False),
                metrics.get("global_network", False),
                metrics.get("gibberish", False),
                metrics.get("device_velocity", False),
                metrics.get("suspicious_name", False),
                metrics.get("geo_velocity", False),
                metrics.get("time_anomaly", False),
                metrics.get("bot_speed", False),
                metrics.get("suspicious_phone", False),
                metrics.get("disposable_email", False),
                metrics.get("email_name_mismatch", False),
                metrics.get("poor_address", False),
                metrics.get("high_risk_pin", False),
                full_config,
                consortium_hits=metrics.get("consortium_hits", 0),
                is_quarantined=metrics.get("is_quarantined", False)
            )
            
            # If original audit had marketplace signals, add them back for a fair comparison
            # We can estimate them if we store them in a future version.
            # For now, we compare simulated_core vs original_full_score.
            
            is_sim_blocked = sim_score > full_config.get("decision_threshold", 50)
            sim_decision = "FORCE_PREPAID" if is_sim_blocked else "ALLOW_COD"
            
            total_sim_score += sim_score
            if is_sim_blocked:
                stats["simulated_blocks"] += 1

            # Transition tracking
            if sim_decision != orig_decision:
                if sim_decision == "FORCE_PREPAID":
                    stats["new_blocks"] += 1
                else:
                    stats["new_approvals"] += 1

        stats["avg_score_original"] = round(total_orig_score / stats["total_scanned"], 1)
        stats["avg_score_simulated"] = round(total_sim_score / stats["total_scanned"], 1)
        
        return stats

simulation_service = SimulationService()
