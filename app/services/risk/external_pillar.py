import logging
import asyncio
from typing import Optional, Any
from app.services.risk.base_pillar import BaseRiskPillar
from app.models.dto.risk_context import RiskContext

class ExternalPillar(BaseRiskPillar):
    """
    Handles GeoIP, VPN Detection, and IP Intelligence.
    """
    def __init__(self):
        super().__init__("External", "vpn_weight")
        self.logger = logging.getLogger("vantix.pillar.external")

    async def evaluate(self, context: RiskContext, risk_config: dict) -> None:
        from app.core.geoip import GEO_READER
        from app.core.redis import r
        
        ip = context.order.ip
        if ip == "127.0.0.1": return

        # Parallelize GeoIP and IP Intelligence checks
        tasks = [
            asyncio.to_thread(GEO_READER.get, ip),
            self._check_ip_intelligence(ip, r)
        ]
        geo_match, is_risky_ip = await asyncio.gather(*tasks)

        if geo_match:
            context.geoip_result = geo_match
            country = geo_match.get("country", {}).get("iso_code")
            if country and country != "IN":
                context.flags.append("RISKY_GEOGRAPHY")
                context.impacts["GEO_RISK"] = float(risk_config.get("geo_velocity_weight", 15.0))

        if is_risky_ip:
            context.flags.append("VPN_OR_ANONYMOUS_IP")
            context.impacts["VPN_DETECTED"] = float(risk_config["vpn_weight"])

    async def _check_ip_intelligence(self, ip: str, redis_client) -> bool:
        cache_key = f"ipint:{ip}"
        cached = await redis_client.get(cache_key)
        if cached is not None: return cached == "1"
        # Dummy logic for example; in production, this calls a 3rd party IP intelligence API
        is_risky = False 
        await redis_client.setex(cache_key, 86400, "1" if is_risky else "0")
        return is_risky
