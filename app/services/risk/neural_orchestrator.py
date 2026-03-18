import asyncio
import logging
from typing import List, Dict, Any
from app.services.risk.base_pillar import BaseRiskPillar
from app.models.dto.risk_context import RiskContext
from app.services.governance_service import governance_service
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
        
        # 1. Fetch Dynamic Governance Weights
        gov_weights = await governance_service.get_adjusted_weights(context.merchant_email)
        
        # 2. Parallel Pillar Execution
        tasks = [p.evaluate(context, risk_config) for p in self.pillars]
        await asyncio.gather(*tasks)
        
        # 3. Cognitive Aggregation (Strategy Pattern)
        score = self._aggregate_score(context, risk_config)
        
        decision = "BLOCK" if score >= risk_config.get("decision_threshold", 50.0) else "ALLOW"
        
        result = {
            "score": round(score, 1),
            "decision": decision,
            "flags": context.flags,
            "impacts": context.impacts,
            "trust_score": context.trust_score
        }
        
        self.log_event("analysis_completed", score=score, decision=decision)
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
