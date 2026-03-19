from typing import List, Dict, Any, Optional
from app.repositories.base_repository import BaseRepository
from app.db.database import AUDIT_STORE
from app.core.redis import rk

class RiskRepository(BaseRepository):
    """
    Handles all Risk Audits, Flags, and Stats persistence.
    Decouples raw DB/Redis calls from the Risk Engine.
    """
    def __init__(self):
        super().__init__("Risk")

    async def save_audit(self, payload: Dict[str, Any]):
        """Persists a risk adjudication to the primary audit store."""
        await AUDIT_STORE.insert_risk_audit(payload)
        
    async def fetch_recent(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves historical audits for a given merchant/team."""
        return await AUDIT_STORE.fetch_recent_risk_audits(team_id, limit=limit)

    async def fetch_profile_audits(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves governance and config change audits."""
        return await AUDIT_STORE.fetch_risk_profile_audits(team_id, limit=limit)

    async def increment_stats(self, key_hash: str, decision: str, savings: float = 0.0):
        """Updates real-time block/savings statistics in Redis."""
        async with self.redis.pipeline() as pipe:
            if decision == "BLOCK":
                pipe.incr(rk(f"stats:blocks:{key_hash}"))
                if savings > 0:
                    pipe.incrbyfloat(rk(f"stats:savings:{key_hash}"), savings)
            pipe.incr(rk("total_blocks")) if decision == "BLOCK" else None
            await pipe.execute()
