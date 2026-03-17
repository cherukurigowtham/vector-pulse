import pytest
import hashlib
import httpx
from app.main import app
from app.core.redis import r

@pytest.mark.asyncio
async def test_behavioral_ingest():
    # Setup: Mock Merchant API Key
    test_key = "vp_test_behavior_key"
    test_email = "test@behavior.ai"
    key_hash = hashlib.sha256(test_key.encode()).hexdigest()
    
    # Seed Redis
    await r.hset(f"apikey:{key_hash}", mapping={
        "email": test_email,
        "plan": "growth"
    })
    
    payload = {
        "session_id": "test_session_v4_ingest",
        "events": [
            {
                "event_type": "pageview",
                "path": "/home",
                "timestamp": 1710672000.0
            },
            {
                "event_type": "click",
                "element": "BUTTON",
                "x": 100,
                "y": 200,
                "path": "/home",
                "timestamp": 1710672005.0
            }
        ],
        "client_metadata": {"ua": "Pytest/Vantix"}
    }
    
    # Ingest using AsyncClient
    from httpx import ASGITransport
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/behavior/ingest",
            json=payload,
            headers={"X-API-Key": test_key}
        )
    
    assert response.status_code == 200
    assert response.json()["events_recorded"] == 2
    
    # Verify in Redis
    key = f"behavior:stream:{test_email}:test_session_v4_ingest"
    
    events = await r.lrange(key, 0, -1)
    assert len(events) == 2
    
    # Cleanup
    await r.delete(key)
    await r.delete(f"apikey:{key_hash}")
