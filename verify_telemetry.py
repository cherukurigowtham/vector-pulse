import asyncio
import json
import time
import os
import sys

# Ensure app is in path
sys.path.append(os.getcwd())

from app.core.redis import r
from app.services.risk_service import run_risk_analysis
from app.models import Order

# Test IP addresses from various regions
TEST_IPS = [
    "1.1.1.1",     # Australia
    "8.8.8.8",     # USA
    "139.5.241.0", # India
    "185.159.157.0",# USA (VPN/Proxy often)
    "91.198.174.192",# Netherlands
    "103.1.204.0", # Hong Kong
    "106.10.128.0",# Japan
    "190.2.146.0", # Argentina
    "41.216.186.0",# South Africa
    "193.161.193.0"# Germany
]

async def verify():
    print("Clearing old telemetry...")
    await r.delete("global:telemetry:geo")
    
    print(f"Simulating {len(TEST_IPS)} global fraud attempts...")
    
    # Mock merchant data
    m_email = "telemetry_test@vantix.com"
    m_key_hash = "test_merchant_hash"
    risk_config = {
        "velocity_window_secs": 60,
        "velocity_max_orders": 5,
        "velocity_weight": 20,
        "sybil_weight": 20,
        "anomaly_weight": 10,
        "identity_weight": 15,
        "vpn_weight": 15,
        "trust_floor": 20,
        "trust_penalty_multiplier": 1.0,
        "history_len": 10,
        "z_score_threshold": 3.0,
        "sybil_address_limit": 3,
        "decision_threshold": 50,
        "global_network_weight": 20,
        "gibberish_weight": 15,
        "device_velocity_weight": 15,
        "suspicious_name_weight": 10,
        "geo_velocity_weight": 25,
        "time_anomaly_weight": 15,
        "bot_speed_weight": 15,
        "suspicious_phone_weight": 15,
        "disposable_email_weight": 15,
        "email_name_mismatch_weight": 15,
        "poor_address_weight": 15,
        "high_risk_pin_weight": 20
    }

    for i, ip in enumerate(TEST_IPS):
        print(f"[{i+1}/{len(TEST_IPS)}] Processing attack from IP: {ip}")
        order = Order(
            uid=f"ATTACK_{i}",
            amt=1000 + (i * 100),
            addr=f"Fraudulent Street {i}, New York",
            pin="110001",
            name="Fraudulent Bot",
            email=f"bot_{i}@fraud.com",
            ip=ip,
            shadow=False
        )
        
        # Trigger risk analysis which should broadcast telemetry
        await run_risk_analysis(order, risk_config, m_key_hash, m_email)
        await asyncio.sleep(0.1) # Small delay
    
    print("\nRetrieving broadcasted telemetry...")
    events_raw = await r.lrange("global:telemetry:geo", 0, -1)
    events = [json.loads(e) for e in events_raw]
    
    print(f"Total events broadcasted: {len(events)}")
    for e in events[:5]:
        print(f" - Event: Lat {e['lat']}, Lon {e['lon']}, Score {e['score']}")
    
    if len(events) >= len(TEST_IPS):
        print("\n✅ Telemetry broadcast verification successful.")
    else:
        print(f"\n❌ Telemetry broadcast failed! Expected {len(TEST_IPS)} but got {len(events)}")

if __name__ == "__main__":
    asyncio.run(verify())
