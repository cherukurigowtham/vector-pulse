import asyncio
from typing import List, Dict, Any
from app.services.risk.base_pillar import BaseRiskPillar
from app.models.dto.risk_context import RiskContext
from app.services.governance_service import governance_service
from app.services.risk.weighting_engine import weighting_engine
from app.core.infrastructure.base_service import BaseService

class NeuralOrchestrator(BaseService):
    """
    Google-Style Central Orchestrator for the Risk Intelligence engine.
    Manages parallel pillar execution and cognitive score aggregation.
    File length: <100 lines.
    """
    def __init__(self, pillars: List[BaseRiskPillar]):
        super().__init__("RiskEngine")
        self.pillars = pillars

    async def analyze(self, context: RiskContext, risk_config: dict) -> Dict[str, Any]:
        """Runs all pillars in parallel and aggregates results."""
        self.log_event("analysis_started", uid=context.order.uid)
        
        # 1. Fetch Dynamic Governance Weights (Classic + Neural)
        gov_weights = await governance_service.get_adjusted_weights(context.merchant_email)
        neural_weights = await weighting_engine.get_weights(context.merchant_email)
        
        # Merge weights: Neural weights take precedence or multiply.
        # For now, we multiply to allow "classic" bounds to still apply.
        effective_weights = {**gov_weights}
        for k, v in neural_weights.items():
             if k in effective_weights: effective_weights[k] *= v
             else: effective_weights[k] = v
        
        # 2. Parallel Pillar Execution with merged config (weights + parameters)
        effective_config = {**risk_config, **effective_weights}
        tasks = [p.evaluate(context, effective_config) for p in self.pillars]
        await asyncio.gather(*tasks)
        
        # 3. Cognitive Aggregation (Strategy Pattern)
        score = self._aggregate_score(context, risk_config)
        
        # 4. Adaptive Resilience (Shield Mode) - Phase 12
        from app.services.risk.shield_monitor import shield_monitor
        from app.services.risk.zk_service import zk_service
        base_threshold = float(risk_config.get("decision_threshold", 50.0))
        
        if await shield_monitor.is_shield_active():
            base_threshold *= 0.8 # Tighten threshold by 20%
            context.flags.append("SHIELD_MODE_ACTIVE")
        
        # 5. Zero-Knowledge Consortium Pulse - Phase 16
        zk_bonus = await zk_service.verify_consortium_risk(
            context.order.email or context.order.phone or "unknown",
            context.merchant_email,
            "consortium_salt_v1"
        )
        if zk_bonus:
            score += zk_bonus
            context.flags.append("ZK_CONSORTIUM_SIGNAL_DETECTED")
            context.impacts["ZK_CONSORTIUM"] = zk_bonus

        decision = "BLOCK" if score >= base_threshold else "ALLOW"
        
        # Record for global monitor
        await shield_monitor.record_decision(decision == "BLOCK")
        
        result = {
            "score": round(float(score), 1),
            "decision": decision,
            "flags": context.flags,
            "impacts": context.impacts,
            "trust_score": context.trust_score
        }
        
        self.log_event("analysis_completed", score=score, decision=decision, shield_active=(decision == "BLOCK" and "SHIELD_MODE_ACTIVE" in context.flags))
        return result

    def _aggregate_score(self, context: RiskContext, risk_config: dict) -> float:
        """Simple weighted summation with cognitive conflict resolution."""
        total_impact = sum(context.impacts.values())
        
        # Trust Factor Resolution
        if context.trust_score > 85.0 and total_impact > 50.0:
            conflict_reduction = (total_impact - 50.0) * 0.3
            context.impacts["COGNITIVE_CONFLICT_RESOLUTION"] = -conflict_reduction
            total_impact -= conflict_reduction
            
        return max(0.0, min(100.0, total_impact))
