from fastapi import APIRouter, Depends, HTTPException
from app.models import Order
from app.core.security import require_api_key
from app.services.risk.factory import get_risk_engine
from app.services.risk.neural_orchestrator import NeuralOrchestrator
from app.models.dto.risk_context import RiskContext
from app.core.config import RISK_CONFIG

router = APIRouter(prefix="/risk", tags=["Risk Analysis"])

@router.post("/scan", summary="Perform real-time fraud analysis on an order.")
async def scan_order(
    order: Order, 
    merchant: dict = Depends(require_api_key),
    engine: NeuralOrchestrator = Depends(get_risk_engine)
):
    """
    Entry point for the modular Risk Engine.
    Leverages parallel pillar execution and cognitive aggregation.
    """
    context = RiskContext(
        order=order,
        merchant_email=merchant["email"],
        merchant_key_hash=merchant["key_hash"]
    )
    
    # Run Orchestrated Analysis
    result = await engine.analyze(context, RISK_CONFIG)
    
    return result
