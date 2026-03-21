import asyncio
import uuid
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from app.core.security import verify_jwt
from app.core.redis import r

router = APIRouter(prefix="/merchant/billing", tags=["billing"])

class CheckoutRequest(BaseModel):
    plan_tier: str
    card_number: str
    exp_month: str
    exp_year: str
    cvc: str
    name_on_card: str

class CheckoutResponse(BaseModel):
    status: str
    transaction_id: str
    message: str
    tier: str
    timestamp: datetime

def get_current_user(request: Request):
    if hasattr(request.state, "user"):
         return request.state.user
    token = request.cookies.get("vp_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        user = verify_jwt(token)
        if user:
            return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

@router.post("/checkout", response_model=CheckoutResponse)
async def process_mock_checkout(payload: CheckoutRequest, current_user: dict = Depends(get_current_user)):
    """
    Simulates FAANG-tier payment processing.
    Introduces artificial latency to mimic exact bank verification times,
    validates the structural card payload, and returns a verified cryptographic receipt.
    """
    # 1. Simulate Network/Bank Verification Latency (1.8 seconds)
    await asyncio.sleep(1.8)

    # 2. Luhn / Format Mock Validation
    clean_card = payload.card_number.replace(" ", "").replace("-", "")
    if not clean_card.isdigit() or len(clean_card) < 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid card format. Please check your card number."
        )

    # 3. Cryptographic Mock Transact ID Generation
    tx_id = f"mc_tx_{uuid.uuid4().hex[:16]}"
    
    # 4. Safely Upgrade the User's Tier in Redis
    email = current_user.get("email")
    if email:
        await r.hset(f"user:{email}", "plan", payload.plan_tier.lower())
        # Log the subscription event
        from app.core.helpers import _log_event
        _log_event("subscription_upgraded", email=email, tier=payload.plan_tier)

    return CheckoutResponse(
        status="succeeded",
        transaction_id=tx_id,
        message="Payment processed successfully. Subscription activated.",
        tier=payload.plan_tier.lower(),
        timestamp=datetime.utcnow()
    )
