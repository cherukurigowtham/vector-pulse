import asyncio
from api_gateway import app, r, _check_velocity, _check_sybil, _check_price_anomaly, _get_trust_score, _check_ip_intelligence
import vector_pulse
import logging
import json

async def verify():
    print("Testing Observability & Governance...")
    
    # 1. Test Single Decision Lifecycle
    print("Lifecycle Test: Check Order -> Store Context -> Explain")
    
    uid = "audit_user_1"
    # Create fake risk event
    from api_gateway import Order
    test_order = Order(uid=uid, amt=9999.0, addr="123 Fraud Lane", pin="110001", ip="8.8.8.8")
    
    # Simulate internal checks
    is_velocity = await _check_velocity(uid)
    is_sybil = await _check_sybil(uid, test_order.addr)
    is_price_anomaly, avg, std = await _check_price_anomaly(uid, test_order.amt)
    trust_score = await _get_trust_score(uid)
    vpn_flag = await _check_ip_intelligence(test_order.ip)
    
    risk_score = vector_pulse.evaluate_weighted_risk(is_velocity, is_sybil, is_price_anomaly, trust_score, vpn_flag)
    risk_id = "test_audit_id"
    
    context = {
        "uid": uid,
        "score": risk_score,
        "metrics": {
            "velocity": is_velocity,
            "sybil": is_sybil,
            "price": is_price_anomaly,
            "trust": trust_score,
            "vpn": vpn_flag
        },
        "timestamp": 123456789
    }
    
    await r.setex(f"explain:{risk_id}", 3600, json.dumps(context))
    print(f"Decision stored for Risk ID: {risk_id} (Score: {risk_score})")

    # 2. Test Explain API logic
    raw_data = await r.get(f"explain:{risk_id}")
    context = json.loads(raw_data)
    m = context["metrics"]
    narrative = []
    if m["vpn"]: narrative.append("VPN detected.")
    if m["price"]: narrative.append("Price anomaly.")
    
    print(f"Explain Result Findings: {narrative}")
    
    # 3. Test Rate Limiting
    from api_gateway import sliding_window_rate_limit
    print("Testing Sliding Window...")
    allowed_1 = await sliding_window_rate_limit("test_key", 100000)
    print(f"RL Allowed (Burst Start): {allowed_1}")

    print("Verification Script Finished.")

if __name__ == "__main__":
    asyncio.run(verify())
