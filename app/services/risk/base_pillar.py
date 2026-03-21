from abc import ABC, abstractmethod
from typing import Optional
from app.models.dto.risk_context import RiskContext

class BaseRiskPillar(ABC):
    """
    Abstract Base Class for all Risk Intelligence Pillars.
    Enforces a strict interface for modular risk evaluation.
    """
    def __init__(self, name: str, weight_key: str):
        self.name = name
        self.weight_key = weight_key

    @abstractmethod
    async def evaluate(self, context: RiskContext, risk_config: dict) -> None:
        """
        Evaluate risk and update the context with flags and impacts.
        Must be idempotent and side-effect free outside the provided context.
        """
        pass
    
    def _get_weight(self, context: RiskContext, risk_config: dict, governance_weights: Optional[dict] = None) -> float:
        """Helper to resolve tuned vs default weights."""
        if governance_weights and self.weight_key in governance_weights:
            return float(governance_weights[self.weight_key])
        return float(risk_config.get(self.weight_key, 0.0))
