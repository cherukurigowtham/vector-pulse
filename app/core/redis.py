import redis.asyncio as redis
from app.core.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_SSL

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
    ssl=REDIS_SSL,
    retry_on_timeout=True,
    health_check_interval=30
)
