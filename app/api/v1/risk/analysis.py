from fastapi import APIRouter, Depends, BackgroundTasks
from app.models import Order
from app.core.security import require_api_key
from app.services.risk.factory import get_risk_engine
from app.services.risk.neural_orchestrator import NeuralOrchestrator
from app.models.dto.risk_context import RiskContext
from app.core.config import RISK_CONFIG
from app.core.redis import r
from app.services.webhook_dispatcher import webhook_dispatcher

router = APIRouter(prefix="/risk", tags=["Risk Analysis"])

@router.post("/scan", summary="Perform real-time fraud analysis on an order.")
async def scan_order(
    order: Order, 
    background_tasks: BackgroundTasks,
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
    
    # Autonomous Outbound Retaliation 
    score = getattr(result, "score", 0.0)
    decision = getattr(result, "decision", "ALLOW_COD")
    
    if score >= 85.0 or decision in ["QUARANTINE_REQUIRED", "FRAUD_CONFIRMED", "FORCE_PREPAID"]:
        payload = {
            "event": "risk.threshold.exceeded",
            "risk_id": getattr(result, "risk_id", "unknown"),
            "order_uid": order.uid,
            "score": score,
            "decision": decision,
            "reasons": getattr(result, "reasons", [])
        }
        background_tasks.add_task(_evaluate_and_dispatch_webhook, merchant["email"], payload)
    
    return result

async def _evaluate_and_dispatch_webhook(email: str, payload: dict):
    """Securely resolves webhook targets entirely outside the main user request event loop."""
    user_data = await r.hgetall(f"user:{email}")
    webhook_url = user_data.get("alert_webhook_url")
    secret = user_data.get("webhook_secret")
    
    if webhook_url:
        await webhook_dispatcher.dispatch_retaliation_alert(webhook_url, payload, secret)
