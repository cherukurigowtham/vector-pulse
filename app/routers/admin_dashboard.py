import time
from fastapi import APIRouter, Depends
from app.core.redis import r
from app.core.security import require_admin

router = APIRouter(prefix="/v1/admin/dashboard", tags=["admin-telemetry"])

@router.get("", summary="Get global CEO television and financial impact telemetry")
async def get_dashboard_stats(_: str = Depends(require_admin)):
    keys = [
        "total_savings_inr",
        "total_blocks",
        "stat:velocity",
        "stat:sybil",
        "stat:price",
        "stat:clusters",
        "stat:geoip"
    ]
    values = await r.mget(keys)
    stats = {k: int(float(v or 0)) for k, v in zip(keys, values)}
    
    return {
        "financial_impact": {
            "total_savings_inr": stats["total_savings_inr"],
            "currency": "INR",
            "impact_label": "Direct RTO Loss Averted"
        },
        "operational_metrics": {
            "total_prevented_frauds": stats["total_blocks"],
            "risk_vector_distribution": {
                "velocity_spikes": stats["stat:velocity"],
                "identity_sybil_patterns": stats["stat:sybil"],
                "price_outliers": stats["stat:price"],
                "fraud_ring_clusters": stats["stat:clusters"],
                "geographic_anomalies": stats["stat:geoip"]
            }
        },
        "system_health": {
            "telemetry_timestamp": time.time(),
            "engine_status": "OPERATIONAL",
            "redis_connection": "ACTIVE"
        }
    }
