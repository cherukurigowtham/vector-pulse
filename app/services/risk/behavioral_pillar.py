import logging
from app.services.risk.base_pillar import BaseRiskPillar
from app.models.dto.risk_context import RiskContext

class BehavioralPillar(BaseRiskPillar):
    """
    Advanced Pillar: Behavioral DNA and Cognitive Signal Analysis.
    """
    def __init__(self):
        super().__init__("Behavior", "bot_speed_weight")
        self.logger = logging.getLogger("vantix.pillar.behavior")

    async def evaluate(self, context: RiskContext, risk_config: dict) -> None:
        from app.services.behavioral_service import analyze_session_behavior
        
        # 1. Static Behavioral DNA (Keystroke/Mouse)
        dna_flags, dna_score = self._check_static_dna(context, risk_config)
        context.flags.extend(dna_flags)
        if dna_score > 0:
            context.impacts["BEHAVIORAL_DNA"] = float(dna_score)

        # 2. Sequential Cognitive Signals (Transformer-based)
        if context.order.session_id:
            behavior_res = await analyze_session_behavior(context.merchant_email, context.order.session_id)
            if behavior_res and "score_impact" in behavior_res:
                impact = behavior_res["score_impact"]
                context.impacts["COGNITIVE_ANOMALY"] = float(impact)
                context.flags.append(f"COGNITIVE_ANOMALY_DETECTED({behavior_res.get('event_count', 0)} events)")

    def _check_static_dna(self, context: RiskContext, risk_config: dict) -> tuple[list[str], int]:
        flags = []
        score = 0
        order = context.order
        weight = risk_config.get("bot_speed_weight", 10.0)

        if order.keystroke_velocity is not None:
            if order.keystroke_velocity < 10 or order.keystroke_velocity > 500:
                flags.append("UNNATURAL_KEYSTROKE_VELOCITY")
                score += weight
                
        if order.mouse_movement_entropy is not None:
            if order.mouse_movement_entropy < 1.0:
                flags.append("BOT_LIKE_MOUSE_MOVEMENT")
                score += weight + 5
            elif order.mouse_movement_entropy > 4.5:
                flags.append("ROBOTIC_CONSISTENCY")
                score += weight
        
        return flags, score
