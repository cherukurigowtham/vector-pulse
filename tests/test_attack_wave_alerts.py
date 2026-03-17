import pytest
import httpx
import time
import asyncio
import hmac
import hashlib
import json
import random
import string
from app.main import app
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.fixture
async def auth_client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        from app.db.database import AUDIT_STORE
        await AUDIT_STORE.init()
        yield ac

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@pytest.mark.asyncio
@patch("app.routers.risk._sliding_window_rate_limit", new_callable=AsyncMock)
async def test_attack_trigger_logic(mock_limit, auth_client):
    """Verifies that risk_service triggers an alert when a fraud ring is detected."""
    ac = auth_client
    mock_limit.return_value = False
    
    ts = int(time.time())
    merchant_email = f"ceo_trigger_test_{ts}_{random_string(4)}@vectorpulse.com"
    signup_res = await ac.post("/auth/signup", json={"email": merchant_email, "password": "Password123!"})
    api_key = signup_res.json()["api_key"]
    headers = {"X-API-Key": api_key}
    
    attacker_payload = {
        "uid": f"attacker_{ts}",
        "amt": 999,
        "phone": "9999999999",
        "email": "attack@fraud.com",
        "addr": "123 Fraud St",
        "pin": "110001",
        "ip": "1.1.1.1"
    }

    # Verify Trigger from Risk Service
    with patch("app.services.risk_service.link_identity", new_callable=AsyncMock) as mock_graph:
        mock_graph.return_value = {"hits": 10, "reputation": {"addr": 0.1, "email": 0.1, "phone": 0.1}}
        
        with patch("app.services.risk_service.dispatch_alert", new_callable=AsyncMock) as mock_dispatch:
            res = await ac.post("/v1/risk-check", json=attacker_payload, headers=headers)
            assert res.status_code == 200
            assert mock_dispatch.called
            args, _ = mock_dispatch.call_args
            assert args[0] == merchant_email
            assert args[1] == "COORDINATED_RING_DETECTED"
            assert args[2]["consortium_hits"] == 10
            print("SUCCESS: Risk Service Triggered Dispatcher")

@pytest.mark.asyncio
async def test_webhook_dispatcher_signing():
    """Verifies that the dispatcher correctly signs and delivers payloads."""
    from app.services.webhook_dispatcher import dispatch_alert
    from app.core.redis import r
    
    merchant_email = "trust_merchant@test.com"
    webhook_url = "https://ops.internal/hook"
    webhook_secret = "very-secret-signing-key-!!!-123"
    
    # Setup mock merchant settings in Redis
    await r.hset(f"user:{merchant_email}", mapping={
        "alert_webhook_url": webhook_url,
        "webhook_secret": webhook_secret
    })
    
    alert_data = {"event": "test_alert", "id": 123}
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        
        await dispatch_alert(merchant_email, "TEST_TYPE", alert_data)
        
        assert mock_post.called
        _, kwargs = mock_post.call_args
        
        sent_payload = kwargs["content"]
        sent_signature = kwargs["headers"]["X-Vector-Pulse-Signature"]
        
        # Recalculate signature locally to verify
        expected_sig = hmac.new(
            webhook_secret.encode(),
            sent_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        assert sent_signature == expected_sig
        payload_json = json.loads(sent_payload)
        assert payload_json["alert_type"] == "TEST_TYPE"
        assert payload_json["data"] == alert_data
        print("SUCCESS: Dispatcher HMAC Signature Verified")
