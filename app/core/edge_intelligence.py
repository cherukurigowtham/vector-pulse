import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis import r

logger = logging.getLogger(__name__)

class EdgeIntelligenceMiddleware(BaseHTTPMiddleware):
    """
    Simulated Edge-Worker Intelligence (Phase 15).
    Intercepts risk checks to provide sub-millisecond blocking for known high-risk 
    identifiers (emails, IPs, devices) before they hit the core Neural Engine.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/v1/risk-check":
            return await call_next(request)
            
        start_time = time.time()
        
        # 1. Parse quick identifiers (Simulating Edge Header Extraction)
        # In a real Cloudflare worker, these would be in headers or a fast KV store.
        try:
            body = await request.json()
            email = body.get("email")
            ip = body.get("ip")
        except:
            return await call_next(request)
            
        # 2. Sub-millisecond Lookup in Edge-Tier Cache (Redis)
        # We check for explicitly blocked consortium signatures or high-confidence trust.
        async with r.pipeline() as pipe:
            if email: pipe.get(f"edge:block:email:{email}")
            if ip: pipe.get(f"edge:block:ip:{ip}")
            res = await pipe.execute()
            
        if any(res):
            latency = (time.time() - start_time) * 1000
            logger.info(f"Edge Block Triggered | Latency: {latency:.2f}ms")
            
            return Response(
                content='{"status":"block","reason":"EDGE_CONSORTIUM_BLOCK","score":100}',
                media_type="application/json",
                status_code=200,
                headers={"X-Vantix-Edge": "HIT", "X-Latency-MS": str(round(latency, 2))}
            )
            
        # Proceed to core Neural Engine if not a certain block/trust
        response = await call_next(request)
        
        # Add latency tracking header for the visualizer
        duration = (time.time() - start_time) * 1000
        response.headers["X-Latency-MS"] = str(round(duration, 2))
        return response
