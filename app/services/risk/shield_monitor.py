import logging
import time
from app.core.redis import r, rk

logger = logging.getLogger(__name__)

class ShieldMonitor:
    """
    Adaptive Resilience - "Shield Mode" (Phase 12).
    Tracks global (prefix-scoped) block rates to detect active attacks.
    If block rate spikes, it triggers 'Shield Mode' to tighten system thresholds.
    """

    def __init__(self):
        self.window = 300 # 5 minute window
        self.threshold_multiplier = 0.7 # Tighten thresholds by 30% when active

    async def record_decision(self, is_blocked: bool):
        """Records a block event for the global monitor."""
        now = time.time()
        ts = int(now)
        # Use a more unique member (ts:nano) to avoid collisions in high-volume bursts
        member = f"{now}"
        
        key = rk("shield:event_log")
        async with r.pipeline() as pipe:
            pipe.zadd(key, {member: ts})
            if is_blocked:
                pipe.zadd(rk("shield:block_log"), {member: ts})
            
            # Cleanup old events
            pipe.zremrangebyscore(key, 0, ts - self.window)
            pipe.zremrangebyscore(rk("shield:block_log"), 0, ts - self.window)
            await pipe.execute()

    async def is_shield_active(self) -> bool:
        """
        Calculates the current block rate. 
        If block rate > 30% and volume > 10 reqs, activate Shield Mode.
        """
        int(time.time())
        total_key = rk("shield:event_log")
        block_key = rk("shield:block_log")
        
        total_reqs = await r.zcard(total_key)
        blocked_reqs = await r.zcard(block_key)
        
        if total_reqs < 10: return False
        
        block_rate = blocked_reqs / total_reqs
        active = block_rate > 0.3
        
        if active:
            logger.warning(f"SHIELD MODE ACTIVE: Block rate at {int(block_rate*100)}%")
            
        return active

shield_monitor = ShieldMonitor()
