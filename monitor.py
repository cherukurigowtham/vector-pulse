import redis
import time
import os
from app.core.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_SSL

# Connect using hardened configuration
r = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    password=REDIS_PASSWORD, 
    ssl=REDIS_SSL,
    db=0, 
    decode_responses=True
)

def show_revenue_dashboard():
    while True:
        try:
            os.system('clear')
            print("=" * 60)
            print("💰  VECTOR-PULSE RTO SHIELD: ENTERPRISE MONITOR  💰")
            print("=" * 60)

            savings = int(r.get("total_savings_inr") or 0)
            blocks = int(r.get("total_blocks") or 0)
            
            print(f"TOTAL LOGISTICS LOSS PREVENTED : ₹{savings:,}")
            print(f"TOTAL FRAUD ORDERS BLOCKED     : {blocks:,}")
            print(f"ESTIMATED MONTHLY PROFIT GAIN  : ₹{savings * 30:,}")
            print("-" * 60)

            print(f"{'FRAUD ENGINE SIGNAL':<25} | COUNT")
            print("-" * 60)
            print(f"{'Identity Clusters (Rust)':<25} | {r.get('stat:clusters') or 0}")
            print(f"{'Sybil/Address Ghosting':<25} | {r.get('stat:sybil') or 0}")
            print(f"{'Price/Amount Anomalies':<25} | {r.get('stat:price') or 0}")
            print(f"{'High Velocity Attacks':<25} | {r.get('stat:velocity') or 0}")
            print(f"{'GeoIP Intelligence':<25} | {r.get('stat:geoip') or 0}")
            print("-" * 60)

            print("LIVE RISK LOGS (Last 10):")
            logs = r.lrange("recent_blocks", 0, 9)
            if logs:
                for log in logs:
                    print(f"  🚩 {log}")
            else:
                print("  ✅ Pipeline clear. No active threats.")

            print("=" * 60)
            print(f"Update time: {time.strftime('%H:%M:%S')} | Interval: 2s")
            time.sleep(2)
        except Exception as e:
            print(f"[!] Monitor Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    show_revenue_dashboard()
