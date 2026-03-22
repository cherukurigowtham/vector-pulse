"""
Redis Sliding Window Rate Limiter
==================================
Protects hot-path endpoints from abuse and brute-force attacks.

Usage (as a FastAPI dependency):
    from app.core.rate_limiter import rate_limit

    @router.post("/scan")
    async def scan_order(
        _: None = Depends(rate_limit(key="risk_scan", limit=100, window=60))
    ):
        ...
"""
import logging
from fastapi import Request, HTTPException, Depends
from app.core.redis import r

logger = logging.getLogger(__name__)


def rate_limit(key: str, limit: int, window: int):
    """
    Sliding window rate limiter using Redis INCR + EXPIRE.

    Args:
        key:    Logical name for the rate limit bucket (e.g. "risk_scan")
        limit:  Maximum requests allowed within the window
        window: Time window in seconds
    """
    async def dependency(request: Request):
        # Build a per-client bucket key: combines the logical key with the client IP or API key
        api_key = request.headers.get("x-api-key", "")
        client_id = api_key or request.client.host if request.client else "unknown"
        bucket_key = f"ratelimit:{key}:{client_id}"

        try:
            current = r.incr(bucket_key)
            if current == 1:
                # First request in this window — set expiry
                r.expire(bucket_key, window)

            if current > limit:
                retry_after = r.ttl(bucket_key)
                logger.warning(
                    f"[RATE LIMIT] Limit exceeded for {key} by {client_id}. "
                    f"Count: {current}/{limit}"
                )
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Max {limit} requests per {window}s.",
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
        except HTTPException:
            raise
        except Exception as e:
            # Redis failure must NOT block the endpoint — fail open, log the error
            logger.error(f"[RATE LIMIT] Redis error, failing open: {e}")

    return Depends(dependency)
