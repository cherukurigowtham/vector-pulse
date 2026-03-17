import json
import logging
from typing import Optional, Dict
from app.core.redis import r

logger = logging.getLogger(__name__)

class DistributedFraudCache:
    """
    Distributed Fraud Cache (DFC) - Phase 15.
    High-speed caching of risk decisions to ensure sub-10ms response times for recurring identities.
    """
    
    TTL = 3600 * 24 # 24 hour decision persistence
    
    async def get_decision(self, email: str, merchant_email: str) -> Optional[Dict]:
        """Sub-10ms decision retrieval."""
        key = f"dfc:{merchant_email}:{email}"
        data = await r.get(key)
        if data:
            logger.info(f"DFC HIT | {email}")
            return json.loads(data)
        return None

    async def update_cache(self, email: str, merchant_email: str, decision_data: Dict):
        """Proactively update the cache after the Neural Engine finishes."""
        key = f"dfc:{merchant_email}:{email}"
        await r.setex(key, self.TTL, json.dumps(decision_data))
        
        # Also sync to edge pre-checks if high-risk
        if decision_data.get("risk_score", 0) > 90:
            await r.setex(f"edge:block:email:{email}", 3600, "1")

dfc = DistributedFraudCache()
