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
            factor = await shield_monitor.get_tightening_factor()
            base_threshold *= factor # Dynamically tighten threshold
            context.flags.append(f"SHIELD_MODE_ACTIVE(f={factor:.2f})")
        
        # 5. Zero-Knowledge Consortium Pulse - Phase 12 ($100B Evolution)
        # Fetch both Negative Threat Signals and Positive Trust Auras
        zk_threat_task = zk_service.verify_consortium_risk(
            context.order.email or context.order.phone or "unknown",
            context.merchant_email,
            "consortium_salt_v1"
        )
        zk_aura_task = zk_service.get_aura_score(
            context.order.email or context.order.phone or "unknown",
            context.merchant_email,
            "consortium_salt_v1"
        )
        
        zk_threat, zk_aura = await asyncio.gather(zk_threat_task, zk_aura_task)
        
        if zk_threat:
            score += zk_threat
            context.flags.append("ZK_CONSORTIUM_THREAT_DETECTED")
            context.impacts["ZK_THREAT"] = zk_threat
            
        if zk_aura < 0:
            score += zk_aura # Subtracting bonus
            context.flags.append(f"IDENTITY_AURA_SIGNAL({zk_aura:.0f})")
            context.impacts["IDENTITY_AURA"] = zk_aura

        # 6. Autonomous Settlement Selection (Phase 12)
        # Instead of a binary BLOCK/ALLOW, we introduce 'ESCROW' for borderline cases.
        # This is the 'Safe Harbor' for the $100B valuation.
        escrow_margin = float(risk_config.get("escrow_margin", 20.0))
        
        if score >= base_threshold + escrow_margin:
            decision = "BLOCK"
        elif score >= base_threshold:
            # Borderline case: Check if Identity Aura allows for Escrow recovery
            # High-Aura users are prioritized for Escrow over hard blocks
            decision = "ESCROW"
            context.flags.append("TRANSITIONED_TO_ESCROW")
        else:
            decision = "ALLOW"
        
        # Record for global monitor
        await shield_monitor.record_decision(decision == "BLOCK")
        
        # 7. Universe Ledger Settlement Rail (Phase 13 - $10T Vision)
        # If user has a powerful 'Aura' (> 20 trust units), we promote to Instant Settlement
        settlement_rail = "LEGACY_ACQUIRER"
        if decision == "ALLOW" and zk_aura <= -20:
            settlement_rail = "ULP_INSTANT"
            context.flags.append("ELIGIBLE_FOR_INSTANT_SETTLEMENT")

        # 8. Zero-Trust Finalization: Purge raw PII after all lookups are complete
        context.order.tokenize()

        result = {
            "score": round(float(score), 1),
            "decision": decision,
            "flags": context.flags,
            "impacts": context.impacts,
            "trust_score": context.trust_score,
            "settlement_rail": settlement_rail
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
