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
        self.window = 600 # 10 minute window for wave detection
        self.base_tighten_ratio = 0.8 # Tighten threshold by 20%
        self.max_tighten_ratio = 0.5 # Maximum tightness (50% reduction)

    async def record_decision(self, is_blocked: bool):
        """Records a block event for the global monitor."""
        now = time.time()
        ts = int(now)
        member = f"{now}"
        
        async with r.pipeline() as pipe:
            pipe.zadd(rk("shield:event_log"), {member: ts})
            if is_blocked:
                pipe.zadd(rk("shield:block_log"), {member: ts})
            
            # Cleanup old events
            pipe.zremrangebyscore(rk("shield:event_log"), 0, ts - self.window)
            pipe.zremrangebyscore(rk("shield:block_log"), 0, ts - self.window)
            await pipe.execute()

    async def record_feedback(self, is_fraud: bool):
        """
        Records human-verified fraud outcomes. 
        Verified fraud is 3x more weighted than engine blocks.
        """
        if not is_fraud: return
        
        now = time.time()
        ts = int(now)
        async with r.pipeline() as pipe:
            pipe.zadd(rk("shield:feedback_log"), {f"f_{now}": ts})
            pipe.zremrangebyscore(rk("shield:feedback_log"), 0, ts - self.window)
            await pipe.execute()
        logger.info("SHIELD: Verified fraud feedback indexed. Immunity strength increasing.")

    async def is_shield_active(self) -> bool:
        """
        Calculates the current risk climate. 
        Combines Engine Block Rate (30% weight) + Verified Fraud spikes (70% weight).
        """
        total_reqs = await r.zcard(rk("shield:event_log"))
        blocked_reqs = await r.zcard(rk("shield:block_log"))
        verified_fraud = await r.zcard(rk("shield:feedback_log"))
        
        if total_reqs < 5: return False # Low volume noise
        
        # Calculate base pressure from blocks
        block_pressure = (blocked_reqs / total_reqs) * 0.4 
        # Calculate acute pressure from human feedback (normalized to 1.0)
        feedback_pressure = min(1.0, (verified_fraud / 10.0)) * 0.6
        
        total_pressure = block_pressure + feedback_pressure
        active = total_pressure > 0.25 # Threshold for activation
        
        if active:
            logger.warning(f"SHIELD MODE ACTIVE: Pressure={total_pressure:.2f} (Blocks={blocked_reqs}, VerifiedFraud={verified_fraud})")
            
        return active

    async def get_tightening_factor(self) -> float:
        """Determines how much to shrink the decision threshold."""
        if not await self.is_shield_active():
            return 1.0
        
        # The higher the pressure, the lower the tightening factor (more aggressive)
        return self.base_tighten_ratio

shield_monitor = ShieldMonitor()
