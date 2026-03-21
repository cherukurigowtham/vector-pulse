import time
import logging
from typing import Dict, Any
from app.core.redis import r

logger = logging.getLogger(__name__)

class TelemetryService:
    """
    Enterprise telemetry for usage-based billing and performance monitoring.
    Tracks:
    - total_scans (per team/merchant)
    - latency_p95 (rolling window)
    - savings_velocity (INR recovered)
    - threat_cluster_density
    """

    def _team_key(self, team_id: str, metric: str) -> str:
        return f"telemetry:{team_id}:{metric}"

    async def record_scan(self, team_id: str, latency_ms: float, risk_score: float, savings_inr: float = 0):
        """
        Record a risk analysis event in the telemetry engine.
        """
        now = time.time()
        today = time.strftime("%Y-%m-%d", time.gmtime(now))
        
        async with r.pipeline() as pipe:
            # 1. Monthly Usage Counter
            month_key = f"telemetry:{team_id}:usage:{today[:7]}"
            pipe.incr(month_key)
            
            # 2. Daily Savings Velocity
            savings_key = f"telemetry:{team_id}:savings:{today}"
            pipe.incrbyfloat(savings_key, savings_inr)
            
            # 3. Latency Percentiles (ZSET for rolling window)
            latency_key = f"telemetry:{team_id}:latency"
            # Element must be unique to avoid overwrites if latencies are same
            pipe.zadd(latency_key, {f"{now}:{latency_ms}": now})
            pipe.zremrangebyscore(latency_key, 0, now - 3600) # Keep 1 hour of data
            
            # 4. Global Pulse Stats
            pipe.incr("telemetry:global:total_scans")
            
            # Set expirations
            pipe.expire(month_key, 86400 * 40)
            pipe.expire(savings_key, 86400 * 30)
            pipe.expire(latency_key, 7200)
            
            await pipe.execute()

    async def get_merchant_stats(self, team_id: str) -> Dict[str, Any]:
        """
        Retrieves aggregated telemetry for the dashboard.
        """
        now = time.time()
        today = time.strftime("%Y-%m-%d", time.gmtime(now))
        month = today[:7]

        usage = await r.get(f"telemetry:{team_id}:usage:{month}")
        savings = await r.get(f"telemetry:{team_id}:savings:{today}")
        
        # Calculate avg latency from ZSET
        # Element is "timestamp:latency"
        nodes = await r.zrange(f"telemetry:{team_id}:latency", 0, -1)
        avg_latency = 0.0
        if nodes:
            latencies = [float(n.split(":")[1]) for n in nodes]
            avg_latency = sum(latencies) / len(latencies)

        return {
            "monthly_usage": int(usage or 0),
            "today_savings_inr": float(savings or 0.0),
            "avg_latency_ms": round(avg_latency, 2),
            "timestamp": now
        }

telemetry_service = TelemetryService()
