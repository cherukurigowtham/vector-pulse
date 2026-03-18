import hashlib
import logging
from typing import Tuple, Optional, Any
from app.services.risk.base_pillar import BaseRiskPillar
from app.models.dto.risk_context import RiskContext

class IdentityPillar(BaseRiskPillar):
    """
    Advanced Pillar: Identity Clustering, Blacklist, and Graph Reputation.
    """
    def __init__(self):
        super().__init__("Identity", "identity_weight")
        self.logger = logging.getLogger("vantix.pillar.identity")

    async def evaluate(self, context: RiskContext, risk_config: dict) -> None:
        import asyncio
        from app.services.graph_service import link_identity
        
        # Graph Reputation & Consortium Check
        graph_res = await link_identity(
            context.order.uid, context.order.email, context.order.phone, 
            context.order.addr, context.order.ip, context.merchant_email
        )
        context.consortium_hits = graph_res.get("hits", 0)
        context.reputation_map = graph_res.get("reputation", {})

        # Blacklist and Clustering checks in parallel
        tasks = [
            self._check_blacklist(context),
            self._check_clustering(context)
        ]
        is_blacklisted, (is_clustered, cluster_score) = await asyncio.gather(*tasks)

        if is_blacklisted:
            context.flags.append("GLOBAL_IDENTITY_BLACKLIST")
            context.impacts["IDENTITY_BLACKLIST"] = float(risk_config["identity_weight"])
        
        if is_clustered:
            context.flags.append("IDENTITY_CLUSTER_DETECTED")
            context.impacts["IDENTITY_CLUSTER"] = cluster_score

        if context.consortium_hits > 0:
            context.flags.append(f"FRAUD_RING_LINK({context.consortium_hits})")
            context.impacts["FRAUD_RING"] = min(5, context.consortium_hits) * float(risk_config.get("global_network_weight", 15.0))

    async def _check_blacklist(self, context: RiskContext) -> bool:
        from app.core.redis import r
        async with r.pipeline() as pipe:
            if context.order.email: pipe.sismember("global:blacklist:email", context.order.email.lower().strip())
            if context.order.phone: pipe.sismember("global:blacklist:phone", context.order.phone.strip())
            res = await pipe.execute()
        return any(res)

    async def _check_clustering(self, context: RiskContext) -> Tuple[bool, float]:
        import vector_pulse
        from app.core.redis import r
        try:
            addr_fp = vector_pulse.address_fingerprint(context.order.addr)
            m_hash = context.merchant_key_hash or "anon"
            
            addr_key = f"cluster:addr:{m_hash}:{hashlib.md5(addr_fp.encode()).hexdigest()}"
            pin_key = f"cluster:pin:{m_hash}:{context.order.pin}"
            
            async with r.pipeline() as pipe:
                pipe.sadd(addr_key, context.order.uid); pipe.scard(addr_key); pipe.expire(addr_key, 86400 * 30)
                pipe.sadd(pin_key, context.order.uid); pipe.scard(pin_key); pipe.expire(pin_key, 86400 * 30)
                res = await pipe.execute()
            
            # Simple heuristic for clustering (shared addr or pin across multiple UIDs)
            shared_addr = res[1]
            shared_pin = res[4]
            return vector_pulse.evaluate_identity_cluster(shared_addr, shared_pin, 0)
        except Exception as e:
            self.logger.error(f"Clustering failed: {e}")
            return False, 0.0
