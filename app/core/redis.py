import os
import redis.asyncio as redis
from redis.asyncio.sentinel import Sentinel
from app.core.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_SSL, REDIS_PREFIX, REDIS_KEY_VERSION

_SENTINEL_HOSTS_RAW = os.getenv("REDIS_SENTINEL_HOSTS", "")
_SENTINEL_MASTER = os.getenv("REDIS_SENTINEL_MASTER", "mymaster")

if _SENTINEL_HOSTS_RAW:
    # Production HA Mode: Redis Sentinel with automatic failover
    _sentinel_hosts = [
        (h.strip().split(":")[0], int(h.strip().split(":")[1]))
        for h in _SENTINEL_HOSTS_RAW.split(",")
    ]
    _sentinel = Sentinel(_sentinel_hosts, socket_timeout=2)
    _r = _sentinel.master_for(
        _SENTINEL_MASTER,
        decode_responses=True,
        password=REDIS_PASSWORD or None,
    )
else:
    # Single-node Mode: Hardened with connection pool + timeouts
    pool_kwargs = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "password": REDIS_PASSWORD,
        "db": 0,
        "decode_responses": True,
        "max_connections": 20,
        "socket_timeout": 2,
        "socket_connect_timeout": 2,
        "retry_on_timeout": True,
        "health_check_interval": 30,
    }
    if REDIS_SSL:
        pool_kwargs["ssl"] = True
        
    _pool = redis.ConnectionPool(**pool_kwargs)
    _r = redis.Redis(connection_pool=_pool)

def rk(key: str) -> str:
    """Prepend the global REDIS_PREFIX and REDIS_KEY_VERSION to the key."""
    prefix = os.getenv("REDIS_PREFIX", REDIS_PREFIX)
    return f"{prefix}:{REDIS_KEY_VERSION}:{key}"

# Alias for backward compatibility or direct use if needed
r = _r
