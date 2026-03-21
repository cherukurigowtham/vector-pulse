import logging
from app.core.redis import r, rk

logger = logging.getLogger(__name__)

class FeatureStore:
    """
    Real-time Feature Store (Phase 11).
    Computes and caches complex derived features (Level 2 Features) 
    that require historical context beyond simple counters.
    """

    async def get_velocity_acceleration(self, merchant_email: str, uid: str) -> float:
        """
        Calculates 'Velocity Acceleration': (L1h Velocity / L24h Average Velocity).
        Detects sudden bursts relative to stable history.
        """
        # Note: In a real system, these would be pre-computed via a stream processor or aggregator.
        # Here we simulate with Redis windowed counts.
        h1_key = rk(f"stats:{merchant_email}:v1h:{uid}")
        h24_key = rk(f"stats:{merchant_email}:v24h:{uid}")
        
        c1h = int(await r.get(h1_key) or 0)
        c24h = int(await r.get(h24_key) or 0)
        
        avg_h1_over_history = c24h / 24.0
        if avg_h1_over_history == 0: return 1.0 # Baseline
        
        return float(c1h / avg_h1_over_history)

    async def get_identity_diversity(self, merchant_email: str, email: str) -> float:
        """
        Calculates 'Identity Diversity': Unique cards/devices for a single email in last 1h.
        """
        set_key = rk(f"diversity:cards:{merchant_email}:{email}")
        unique_count = await r.scard(set_key)
        return float(unique_count)

    async def record_event(self, merchant_email: str, email: str, card_bin: str):
        """Updates diversity sets."""
        set_key = rk(f"diversity:cards:{merchant_email}:{email}")
        await r.sadd(set_key, card_bin)
        await r.expire(set_key, 3600) # 1h window

feature_store = FeatureStore()
