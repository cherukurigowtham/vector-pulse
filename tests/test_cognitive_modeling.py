import pytest
import hashlib
import httpx
import time
import json
from app.main import app
from app.core.redis import r

@pytest.mark.asyncio
async def test_cognitive_behavioral_risk_integration():
    # 1. Setup Mock Merchant
    test_key = "vp_test_cog_key"
    test_email = "cog@vantix.ai"
    key_hash = hashlib.sha256(test_key.encode()).hexdigest()
    await r.hset(f"apikey:{key_hash}", mapping={"email": test_email, "plan": "growth"})
    
    session_id = "v4_test_cog_session_999"
    
    # 2. Simulate BOT-LIKE behavioral stream in Redis (Low Entropy)
    # Rhythmic clicks every 1 second exactly
    stream_key = f"behavior:stream:{test_email}:{session_id}"
    events = []
    for i in range(10):
        events.append({
            "event_type": "click",
            "path": "/checkout",
            "timestamp": 1710672000.0 + i, # Perfect 1s intervals (Zero Entropy)
            "server_received_at": time.time()
        })
    # Add a fast form fill anomaly
    events.append({
        "event_type": "blur",
        "element": "card_number",
        "dwell_time_ms": 10, # Bot Speed
        "path": "/checkout",
        "timestamp": 1710672011.0,
        "server_received_at": time.time()
    })
    
    await r.rpush(stream_key, *[json.dumps(e) for e in events])
    
    # 3. Submit Order referencing the same session
    order_payload = {
        "uid": "ord_cog_123",
        "amt": 500.0,
        "addr": "123 Test Street, Bangalore",
        "pin": "560001",
        "name": "Bot Tester",
        "email": "bot@test.com",
        "phone": "9876543210",
        "ip": "1.1.1.1",
        "session_id": session_id
    }
    
    from httpx import ASGITransport
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/risk-check",
            json=order_payload,
            headers={"X-API-Key": test_key}
        )
    
    assert response.status_code == 200
    res = response.json()
    
    # 4. Verify Cognitive Flags are present
    flags = res.get("risk_factors", [])
    print(f"DEBUG FLAGS: {flags}")
    print(f"DEBUG SCORE: {res.get('risk_score')}")
    
    assert any("COGNITIVE_ANOMALY_DETECTED" in f for f in flags)
    assert "LOW_INTERACTION_ENTROPY" in flags
    
    assert res["risk_score"] > 20 # Baseline + Cog penalties
    
    # Cleanup
    await r.delete(stream_key)
    await r.delete(f"apikey:{key_hash}")
