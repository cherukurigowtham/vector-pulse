import redis.asyncio as redis
from app.core.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_SSL, REDIS_PREFIX, REDIS_KEY_VERSION

_r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
    ssl=REDIS_SSL,
    health_check_interval=30
)

import os

def rk(key: str) -> str:
    """Prepend the global REDIS_PREFIX and REDIS_KEY_VERSION to the key."""
    prefix = os.getenv("REDIS_PREFIX", REDIS_PREFIX)
    return f"{prefix}:{REDIS_KEY_VERSION}:{key}"

# Alias for backward compatibility or direct use if needed
r = _r
