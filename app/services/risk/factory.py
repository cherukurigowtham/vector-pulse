from app.services.risk.velocity_pillar import VelocityPillar
from app.services.risk.identity_pillar import IdentityPillar
from app.services.risk.behavioral_pillar import BehavioralPillar
from app.services.risk.external_pillar import ExternalPillar
from app.services.risk.neural_orchestrator import NeuralOrchestrator

# Dependency Injection / Factory: Create the engine instance
# This can be injected via FastAPI Depends()
def get_risk_engine() -> NeuralOrchestrator:
    pillars = [
        VelocityPillar(),
        IdentityPillar(),
        BehavioralPillar(),
        ExternalPillar()
    ]
    return NeuralOrchestrator(pillars)
