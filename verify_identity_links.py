import asyncio
import json
import time
import os
import sys

# Ensure app is in path
sys.path.append(os.getcwd())

from app.services.identity_linker import identity_linker
from app.services.risk_service import run_risk_analysis
from app.models import Order

async def verify():
    print("Preparing 'Shadow Ring' simulation...")
    
    shared_ip = "192.168.1.100"
    shared_device = "DEV_SHADOW_RING_99"
    merchant_email = "test_merchant@vantix.com"
    merchant_key_hash = "test_hash"
    
    risk_config = {
        "velocity_window_secs": 3600,
        "velocity_max_orders": 5,
        "sybil_address_limit": 3,
        "history_len": 10,
        "z_score_threshold": 3.0,
        "trust_floor": 20.0,
        "trust_penalty_multiplier": 1.0,
        "velocity_weight": 10.0,
        "sybil_weight": 20.0,
        "anomaly_weight": 10.0,
        "identity_weight": 25.0,
        "vpn_weight": 15.0,
        "global_network_weight": 20.0,
        "gibberish_weight": 15.0,
        "device_velocity_weight": 20.0,
        "suspicious_name_weight": 10.0,
        "geo_velocity_weight": 25.0,
        "time_anomaly_weight": 5.0,
        "bot_speed_weight": 10.0,
        "suspicious_phone_weight": 10.0,
        "disposable_email_weight": 10.0,
        "email_name_mismatch_weight": 10.0,
        "poor_address_weight": 10.0,
        "high_risk_pin_weight": 10.0
    }

    # 1. Warm up the identity graph with 6 different emails on the SAME IP/Device
    print("Linking 6 identities to a single shared IP/Device...")
    for i in range(6):
        email = f"attacker_{i}@fraud.com"
        await identity_linker.link_identities(email, shared_ip, shared_device)
        print(f" Linked: {email}")

    # 2. Run risk analysis for the 7th identity in the cluster
    target_email = "target_fraudster@fraud.com"
    print(f"\nAnalyzing 7th identity: {target_email}")
    
    order = Order(
        uid="U_SHADOW_7",
        amt=100.0,
        addr="123 Fraud Lane, Bangalore",
        ip=shared_ip,
        email=target_email,
        name="Fraudulent User",
        phone="9999999999",
        pin="560001",
        device_hash=shared_device,
        session_id="S_FRAUD_7_LONG_SESSION_ID"
    )
    
    result = await run_risk_analysis(order, risk_config, merchant_key_hash, merchant_email)
    
    # 3. Verify 'SHADOW_RING_DETECTED' flag and impact
    print("\nRisk Analysis Results:")
    print(f" Score: {result['score']}")
    print(f" Flags: {result['flags']}")
    
    if any("SHADOW_RING_DETECTED" in f for f in result['flags']):
        print("✅ Success: Shadow Ring Detected!")
    else:
        print("❌ Failed: Shadow Ring NOT detected in flags.")

    # 4. Verify Identity Graph Retrieval
    print("\nVerifying Identity Graph Retrieval...")
    graph = await identity_linker.get_identity_graph("ip", shared_ip)
    print(f" Emails linked to IP {shared_ip}: {len(graph.get('emails', []))}")
    if len(graph.get('emails', [])) >= 6:
        print("✅ Success: Identity Graph correctly populated.")
    else:
        print(f"❌ Failed: Expected at least 6 linked emails, got {len(graph.get('emails', []))}")

if __name__ == "__main__":
    asyncio.run(verify())
