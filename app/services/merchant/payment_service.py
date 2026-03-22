import uuid
import time
from typing import List, Dict, Any
from app.core.infrastructure.base_service import BaseService
from app.repositories.base_repository import BaseRepository

class PaymentService(BaseService):
    """
    Simulates Razorpay Payment Gateway for usage-based billing.
    Provides order creation, verification, and history management.
    """
    def __init__(self, repo: BaseRepository):
        super().__init__("Payment")
        self.repo = repo
        self.key_secret = "mock_secret_key_12345" # Injected in real world

    async def create_order(self, team_id: str, amount_inr: float) -> Dict[str, Any]:
        """Generates a mock Razorpay Order."""
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        order_data = {
            "id": order_id,
            "entity": "order",
            "amount": int(amount_inr * 100), # Razorpay uses paise
            "currency": "INR",
            "receipt": f"rcpt_{team_id}_{int(time.time())}",
            "status": "created",
            "created_at": int(time.time())
        }
        
        # Persist to Redis/DB as PENDING
        await self.repo.redis.hset(f"payment_order:{order_id}", mapping={
            "team_id": team_id,
            "amount": amount_inr,
            "status": "PENDING",
            "timestamp": time.time()
        })
        
        return order_data

    async def verify_payment(self, payload: Dict[str, Any]) -> bool:
        """
        Simulates Razorpay Signature Verification.
        Expects: razorpay_order_id, razorpay_payment_id, razorpay_signature
        """
        order_id = payload.get("razorpay_order_id")
        payment_id = payload.get("razorpay_payment_id")
        signature = payload.get("razorpay_signature")
        
        if not all([order_id, payment_id, signature]):
            return False

        # Mock Signature Verification: In real world, we use HMAC-SHA256
        # generated_sig = hmac.new(
        #     self.key_secret.encode(),
        #     f"{order_id}|{payment_id}".encode(),
        #     hashlib.sha256
        # ).hexdigest()
        
        # For Mock: We accept all signatures starting with 'mock_sig_'
        is_valid = signature.startswith("mock_sig_")
        
        if is_valid:
            # Update status in persistence
            order_info = await self.repo.redis.hgetall(f"payment_order:{order_id}")
            if order_info:
                team_id = order_info.get("team_id")
                amount = order_info.get("amount")
                
                async with self.repo.redis.pipeline() as pipe:
                    pipe.hset(f"payment_order:{order_id}", "status", "SUCCESS")
                    pipe.lpush(f"billing_history:{team_id}", f"PAID:{amount}:{time.time()}:{payment_id}")
                    await pipe.execute()
                    
                self.logger.info(f"Payment SUCCESS for order {order_id} (Team: {team_id})")
                return True
        
        self.logger.warning(f"Payment VERIFICATION FAILED for order {order_id}")
        return False

    async def get_history(self, team_id: str) -> List[Dict[str, Any]]:
        """Retrieves simulated billing history."""
        history_raw = await self.repo.redis.lrange(f"billing_history:{team_id}", 0, 10)
        history = []
        for item in history_raw:
            parts = item.split(":")
            if len(parts) >= 4:
                history.append({
                    "status": parts[0],
                    "amount": float(parts[1]),
                    "timestamp": float(parts[2]),
                    "payment_id": parts[3]
                })
        return history
