import redis
import os

# Use the same logic to find the host
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

def reset():
    print(f"♻️  Connecting to {REDIS_HOST}...")
    # This clears all keys in the current DB
    r.flushdb()
    print("✅ System Cleaned. All blacklists and counters removed.")

if __name__ == "__main__":
    reset()
