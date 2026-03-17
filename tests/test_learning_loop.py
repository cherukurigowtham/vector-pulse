import pytest
import httpx
import time
import json
import asyncio
import random
import string
from app.main import app
from app.core.redis import r
from unittest.mock import patch, AsyncMock

def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@pytest.fixture
async def auth_client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        from app.db.database import AUDIT_STORE
        await AUDIT_STORE.init()
        yield ac

@pytest.mark.asyncio
@patch("app.routers.risk._sliding_window_rate_limit", new_callable=AsyncMock)
async def test_learning_loop_rto_penalty(mock_limit, auth_client):
    ac = auth_client
    mock_limit.return_value = False
    ts = int(time.time())
    merchant_email = f"ceo_test_{ts}_{random_string(4)}@vectorpulse.com"
    password = "StrongPassword123!"
    
    # Setup: Create merchant and get API key
    signup_res = await ac.post("/auth/signup", json={"email": merchant_email, "password": password})
    api_key = signup_res.json()["api_key"]
    headers = {"X-API-Key": api_key}
    
    # 1. First Risk Check (Baseline)
    order_data = {
        "uid": f"user_{ts}_{random_string(4)}",
        "amt": 1500, # Moderate amount
        "phone": f"8{random.randint(100000000, 999999999)}",
        "email": f"user_{ts}_{random_string(4)}@gmail.com",
        "addr": f"123 {random_string(8)} Road, Bangalore", # Sane address
        "pin": f"{random.randint(110001, 600000)}",
        "ip": f"{random.randint(10, 200)}.{random.randint(10, 200)}.{random.randint(10, 200)}.{random.randint(10, 200)}"
    }
    
    res1 = await ac.post("/v1/risk-check", json=order_data, headers=headers)
    assert res1.status_code == 200
    score1 = res1.json()["risk_score"]
    risk_id = res1.json()["risk_id"]
    factors1 = res1.json()["risk_factors"]
    
    print(f"BASELINE: Score: {score1}, Factors: {factors1}")
    
    # 2. Provide RTO Feedback
    res_fb = await ac.post("/v1/outcome", json={"risk_id": risk_id, "status": "RTO", "reason": "Strategic Fraud Feedback"}, headers=headers)
    assert res_fb.status_code == 200
    
    # Wait for background task
    await asyncio.sleep(2.0)
    
    # 3. Second Risk Check (Same Order)
    res2 = await ac.post("/v1/risk-check", json=order_data, headers=headers)
    score2 = res2.json()["risk_score"]
    factors2 = res2.json()["risk_factors"]
    
    print(f"LEARNED: Score: {score2}, Factors: {factors2}")
    
    # Verify the Learning Brain improved its sensitivity
    assert score2 > score1, "Learning Brain should increase risk score after RTO feedback"
    print("SUCCESS: Adaptive Intelligence verified.")
