import time
import logging
from app.services.risk.base_pillar import BaseRiskPillar
from app.models.dto.risk_context import RiskContext
from app.core.redis import r, rk
from app.services.risk.feature_store import feature_store

class VelocityPillar(BaseRiskPillar):
    """
    Consolidates Local, Global, and Device-based frequency analysis.
    """
    def __init__(self):
        super().__init__("Velocity", "velocity_weight")
        self.logger = logging.getLogger("vantix.pillar.velocity")

    async def evaluate(self, context: RiskContext, risk_config: dict) -> None:
        """Parallel check of all velocity vectors."""
        import asyncio
        
        # We can run these in parallel internally for better pillar performance
        tasks = [
            self._check_local_velocity(context, risk_config),
            self._check_global_velocity(context, risk_config),
            self._check_device_velocity(context, risk_config)
        ]
        
        results = await asyncio.gather(*tasks)
        is_local, is_global, is_device = results
        
        if is_local:
            context.flags.append("HIGH_VELOCITY")
            context.impacts["HIGH_VELOCITY"] = float(risk_config["velocity_weight"])
        
        if is_global:
            context.flags.append("GLOBAL_VELOCITY_SPIKE")
            context.impacts["GLOBAL_VELOCITY"] = float(risk_config["velocity_weight"]) * 0.5
            
        if is_device:
            context.flags.append("DEVICE_FINGERPRINT_VELOCITY")
            context.impacts["DEVICE_VELOCITY"] = float(risk_config.get("device_velocity_weight", 15.0))

        # 4. Neural Velocity Acceleration (Phase 11)
        acceleration = await feature_store.get_velocity_acceleration(context.merchant_email, context.order.uid)
        if acceleration > 3.0: # Burst detected
            context.flags.append("VELOCITY_ACCELERATION")
            context.impacts["VELOCITY_ACCELERATION"] = float(risk_config.get("velocity_weight", 20.0)) * 0.5

    async def _check_local_velocity(self, context: RiskContext, risk_config: dict) -> bool:
        now = time.time()
        window = risk_config["velocity_window_secs"]
        # Merchant-scoped key
        key = rk(f"velocity:{context.merchant_key_hash or 'anon'}:{context.order.uid}")
        async with r.pipeline() as pipe:
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.expire(key, window * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"]

    async def _check_global_velocity(self, context: RiskContext, risk_config: dict) -> bool:
        now = time.time()
        window = risk_config["velocity_window_secs"]
        key = rk(f"global:velocity:ip:{context.order.ip}")
        async with r.pipeline() as pipe:
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.expire(key, window * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"] * 10

    async def _check_device_velocity(self, context: RiskContext, risk_config: dict) -> bool:
        if not context.order.device_hash: return False
        now = time.time()
        window = risk_config["velocity_window_secs"]
        key = rk(f"device:velocity:{context.order.device_hash}")
        async with r.pipeline() as pipe:
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.expire(key, window * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"]
