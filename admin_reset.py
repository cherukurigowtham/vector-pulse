import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
RESET_CONFIRM = os.getenv("VECTOR_PULSE_RESET_CONFIRM", "")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

def reset():
    if RESET_CONFIRM != "DELETE_ALL_DATA":
        raise RuntimeError(
            "Refusing to flush Redis. Set VECTOR_PULSE_RESET_CONFIRM=DELETE_ALL_DATA to proceed."
        )

    print(f"Connecting to {REDIS_HOST}...")
    r.flushdb()
    print("Redis database flushed.")

if __name__ == "__main__":
    reset()
