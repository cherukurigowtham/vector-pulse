from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any
from app.core.security import require_role
from app.repositories.base_repository import BaseRepository
from app.services.merchant.payment_service import PaymentService

router = APIRouter(tags=["Payments"])

# Dependency Injection
def get_payment_service():
    repo = BaseRepository("Payment")
    return PaymentService(repo)

@router.post("/merchant/payments/orders")
async def create_payment_order(
    payload: Dict[str, Any],
    user = Depends(require_role(["ADMIN", "ANALYST"])),
    svc: PaymentService = Depends(get_payment_service)
):
    """Initiates a mock Razorpay payment order."""
    amount = payload.get("amount")
    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    order = await svc.create_order(user["team_id"], amount)
    return order

@router.post("/merchant/payments/verify")
async def verify_payment(
    payload: Dict[str, Any],
    user = Depends(require_role(["ADMIN", "ANALYST"])),
    svc: PaymentService = Depends(get_payment_service)
):
    """Verifies a mock Razorpay payment signature."""
    success = await svc.verify_payment(payload)
    if not success:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    
    return {"status": "success", "message": "Payment verified and recorded"}

@router.get("/merchant/payments/history")
async def get_payment_history(
    user = Depends(require_role(["ADMIN", "ANALYST", "VIEWER"])),
    svc: PaymentService = Depends(get_payment_service)
):
    """Retrieves billing history for the team."""
    history = await svc.get_history(user["team_id"])
    return {"history": history}
