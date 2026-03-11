import redis
import time
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

def show_revenue_dashboard():
    while True:
        os.system('clear')
        print("=" * 60)
        print("💰  VECTOR-PULSE RTO SHIELD: ENTERPRISE MONITOR  💰")
        print("=" * 60)

        savings = int(r.get("total_savings_inr") or 0)
        print(f"TOTAL LOGISTICS LOSS PREVENTED : ₹{savings:,}")
        print(f"ESTIMATED MONTHLY PROFIT GAIN  : ₹{savings * 30:,}")
        print("-" * 60)

        print(f"{'FRAUD TYPE':<18} | COUNT")
        print(f"{'Sybil Attacks':<18} | {r.get('stat:sybil') or 0}")
        print(f"{'Price Anomalies':<18} | {r.get('stat:price') or 0}")
        print(f"{'High Velocity':<18} | {r.get('stat:velocity') or 0}")
        print("-" * 60)

        print("LIVE FLAGGED ORDERS:")
        logs = r.lrange("recent_blocks", 0, 9)
        if logs:
            for log in logs:
                print(f"  🚩 {log}")
        else:
            print("  ✅ No blocks yet.")

        print("=" * 60)
        time.sleep(1)


if __name__ == "__main__":
    show_revenue_dashboard()
