import logging
import random
from typing import Dict
from app.core.redis import r, rk
from app.core.config import RISK_CONFIG

logger = logging.getLogger(__name__)

class NeuralWeightingEngine:
    """
    Advanced RL-inspired Weighting Engine (Phase 9).
    Uses a Thompson Sampling approach to dynamically adjust pillar weights
    based on historical accuracy and real-time feedback.
    """

    def __init__(self):
        self.default_weights = {
            "velocity": RISK_CONFIG.get("velocity_weight", 1.0),
            "sybil": RISK_CONFIG.get("sybil_weight", 1.0),
            "anomaly": RISK_CONFIG.get("anomaly_weight", 1.0),
            "behavioral": 1.0,
            "external": 1.0
        }

    async def get_weights(self, merchant_email: str) -> Dict[str, float]:
        """
        Calculates weights using Thompson Sampling from Beta distributions (alpha, beta).
        alpha = success count, beta = failure count.
        """
        stats_key = rk(f"neural:weights:stats:{merchant_email}")
        stats = await r.hgetall(stats_key) or {}
        
        sampled_weights = {}
        for pillar in self.default_weights.keys():
            alpha = float(stats.get(f"{pillar}:alpha", 1.0))
            beta = float(stats.get(f"{pillar}:beta", 1.0))
            
            # Sample from Beta distribution (simplified for now with random.betavariate)
            # In a high-perf environment, we'd use numpy or a faster math lib.
            sample = random.betavariate(alpha, beta)
            
            # Scale the sample by the base weight
            sampled_weights[f"{pillar}_weight"] = sample * self.default_weights[pillar] * 2.0
            
        return sampled_weights

    async def update_stats(self, merchant_email: str, decisions: Dict[str, bool], feedback: str):
        """
        Updates the Alpha/Beta parameters based on feedback.
        feedback: "TRUE_POSITIVE", "FALSE_POSITIVE", "TRUE_NEGATIVE", "FALSE_NEGATIVE"
        """
        stats_key = rk(f"neural:weights:stats:{merchant_email}")
        
        async with r.pipeline() as pipe:
            for pillar, fired in decisions.items():
                if not fired: continue
                
                if feedback == "TRUE_POSITIVE" or feedback == "TRUE_NEGATIVE":
                    # Correct decision: increase Alpha
                    pipe.hincrbyfloat(stats_key, f"{pillar}:alpha", 0.1)
                elif feedback == "FALSE_POSITIVE" or feedback == "FALSE_NEGATIVE":
                    # Incorrect decision: increase Beta
                    pipe.hincrbyfloat(stats_key, f"{pillar}:beta", 0.1)
            
            await pipe.execute()
        
        logger.info(f"NeuralWeighting: Updated stats for {merchant_email} based on {feedback}")

weighting_engine = NeuralWeightingEngine()
