import time
import logging
from app.core.redis import r, rk

logger = logging.getLogger(__name__)

class EscrowService:
    """
    The Flow Engine: Autonomous Trust Escrows (Phase 12).
    Locks funds/transactions in a 'Safe Harbor' for behavioral verification.
    This prevents false positives and recovers lost revenue.
    """

    def __init__(self):
        self.default_ttl = 3600 # 1 hour escrow lock

    async def lock_transaction(self, risk_id: str, merchant_id: str, amount: float, reason: str):
        """
        Places a transaction in the Escrow Registry.
        """
        key = rk(f"escrow:lock:{risk_id}")
        payload = {
            "m_id": merchant_id,
            "amt": amount,
            "reason": reason,
            "ts": time.time(),
            "status": "LOCKED"
        }
        await r.hset(key, mapping=payload)
        await r.expire(key, self.default_ttl)
        
        # Add to merchant's active escrow set
        await r.sadd(rk(f"escrow:active:{merchant_id}"), risk_id)
        logger.info(f"[ESCROW] Transaction {risk_id} locked. Reason: {reason}")
        return True

    async def release_transaction(self, risk_id: str) -> bool:
        """
        Releases a transaction from escrow after successful verification.
        """
        key = rk(f"escrow:lock:{risk_id}")
        data = await r.hgetall(key)
        if not data:
            return False
            
        merchant_id = data.get("m_id")
        async with r.pipeline() as pipe:
            pipe.hset(key, "status", "RELEASED")
            pipe.srem(rk(f"escrow:active:{merchant_id}"), risk_id)
            pipe.expire(key, 86400) # Keep record for 24h
            await pipe.execute()
            
        logger.info(f"[ESCROW] Transaction {risk_id} RELEASED to merchant {merchant_id}.")
        return True

    async def get_stats(self, merchant_id: str):
        """Returns the total value currently held in escrow for a merchant."""
        active_ids = await r.smembers(rk(f"escrow:active:{merchant_id}"))
        total_value = 0.0
        for rid in active_ids:
            val = await r.hget(rk(f"escrow:lock:{rid}"), "amt")
            if val: total_value += float(val)
        return {"active_count": len(active_ids), "total_value_locked": total_value}

escrow_service = EscrowService()
