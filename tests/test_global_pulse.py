import pytest
import httpx
import time
import asyncio
import random
import string
from app.main import app
from unittest.mock import patch, AsyncMock

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@pytest.fixture
async def auth_client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        from app.db.database import AUDIT_STORE
        await AUDIT_STORE.init()
        yield ac

@pytest.mark.asyncio
@patch("app.routers.risk._sliding_window_rate_limit", new_callable=AsyncMock)
async def test_global_pulse_collective_defense(mock_limit, auth_client):
    ac = auth_client
    mock_limit.return_value = False
    
    # 1. Setup: Two distinct merchants
    ts = int(time.time())
    m1_email = f"merchant_a_{ts}_{random_string(4)}@test.com"
    m2_email = f"merchant_b_{ts}_{random_string(4)}@test.com"
    pw = "StrongPass123!"
    
    res_m1 = await ac.post("/auth/signup", json={"email": m1_email, "password": pw})
    key1 = res_m1.json()["api_key"]
    
    res_m2 = await ac.post("/auth/signup", json={"email": m2_email, "password": pw})
    key2 = res_m2.json()["api_key"]
    
    # 2. Shared Identity Attributes (The "Attacker")
    attacker_data = {
        "uid": f"attacker_{ts}",
        "amt": 500,
        "phone": f"9{random.randint(100000000, 999999999)}",
        "email": f"fraud_{ts}_{random_string(4)}@gmail.com",
        "addr": f"Plot {random.randint(1,100)}, Fraud Lane, Bangalore",
        "pin": "560001",
        "ip": "1.2.3.4"
    }
    
    # 3. Merchant A: Baseline Check
    headers1 = {"X-API-Key": key1}
    res_a1 = await ac.post("/v1/risk-check", json=attacker_data, headers=headers1)
    score_a1 = res_a1.json()["risk_score"]
    risk_id_a = res_a1.json()["risk_id"]
    print(f"Merchant A Baseline: {score_a1}")
    
    # 4. Merchant A: Reports RTO (Fraud)
    # This should drop the Global Reputation of the email/phone/addr
    res_outcome = await ac.post("/v1/outcome", json={"risk_id": risk_id_a, "status": "RTO", "reason": "Consistent Fraud"}, headers=headers1)
    assert res_outcome.status_code == 200
    
    # Wait for Global Pulse to propagate reputation drift
    await asyncio.sleep(2.0)
    
    # 5. Merchant B: Checks SAME Attacker
    headers2 = {"X-API-Key": key2}
    res_b = await ac.post("/v1/risk-check", json=attacker_data, headers=headers2)
    score_b = res_b.json()["risk_score"]
    factors_b = res_b.json()["risk_factors"]
    
    print(f"Merchant B Score for same identity: {score_b}")
    print(f"Factors for Merchant B: {factors_b}")
    
    # Verify Collective Defense
    assert score_b > score_a1, "Merchant B should see a HIGHER risk score due to Merchant A's feedback"
    assert "GLOBAL_REPUTATION_WARNING" in factors_b, "Global Pulse reputation warning should be triggered"
    assert "CROSS_MERCHANT_FRAUD_RING_DETECTED(1)" in factors_b, "Graph linking should detect the shared identity"
