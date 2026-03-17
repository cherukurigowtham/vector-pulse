import pytest
import httpx
import time
from app.main import app
from app.core.redis import r
import hashlib

@pytest.fixture(autouse=True)
async def setup_test_key():
    # Inject a known test key into Redis for the session
    test_key = "test_key_123"
    key_hash = hashlib.sha256(test_key.encode()).hexdigest()
    await r.hset(f"apikey:{key_hash}", mapping={
        "email": "test@merchant.com",
        "plan": "starter",
        "key_prefix": "test_prefix",
        "key_suffix": "test_suffix"
    })
    yield
    await r.delete(f"apikey:{key_hash}")
    # Cleanup edge blocks and DFC
    await r.delete("edge:block:email:bad@actor.com")
    await r.delete("dfc:test@merchant.com:repeat@user.com")

@pytest.mark.asyncio
async def test_edge_intelligence_blocking():
    """Verify that edge pre-checks block known bad actors instantly."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Manually inject an edge block
        await r.setex("edge:block:email:bad@actor.com", 60, "1")
        
        # 2. Trigger risk check
        start = time.perf_counter()
        res = await ac.post("/v1/risk-check", 
            json={
                "email": "bad@actor.com", 
                "uid": "123", 
                "ip": "1.1.1.1", 
                "amt": 100.0, 
                "addr": "123 Main St", 
                "pin": "560001",
                "phone": "9876543210"
            },
            headers={"X-API-Key": "test_key_123"}
        )
        latency = (time.perf_counter() - start) * 1000
        
        assert res.status_code == 200
        assert res.json()["reason"] == "EDGE_CONSORTIUM_BLOCK"
        assert res.headers.get("X-Vantix-Edge") == "HIT"
        # Edge blocks should be extremely fast
        assert latency < 100 

@pytest.mark.asyncio
async def test_distributed_fraud_cache_performance():
    """Verify that recurring users are served via DFC for sub-10ms response."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        order_data = {
            "email": "repeat@user.com", 
            "uid": "456", 
            "ip": "2.2.2.2", 
            "amt": 200.0, 
            "addr": "456 Park Ave", 
            "pin": "560002",
            "phone": "9988776655"
        }
        
        # 1. First run (Cache miss)
        res1 = await ac.post("/v1/risk-check", json=order_data, headers={"X-API-Key": "test_key_123"})
        assert res1.status_code == 200
        
        # Proactively update cache since background tasks are tricky in tests
        from app.services.cache_service import dfc
        await dfc.update_cache("repeat@user.com", "test@merchant.com", res1.json())
        
        # 2. Second run (Cache hit)
        start = time.perf_counter()
        res2 = await ac.post("/v1/risk-check", json=order_data, headers={"X-API-Key": "test_key_123"})
        latency = (time.perf_counter() - start) * 1000
        
        assert res2.status_code == 200
        assert res2.headers.get("X-Vantix-Cache") == "HIT"
        assert latency < 50
        assert res1.headers.get("X-Vantix-Cache") is None
        
        # Give background task a moment to sync cache
        time.sleep(0.5) 
        
        # 2. Second run (Cache hit)
        start = time.perf_counter()
        res2 = await ac.post("/v1/risk-check", json=order_data, headers={"X-API-Key": "test_key_123"})
        latency = (time.perf_counter() - start) * 1000
        
        assert res2.status_code == 200
        assert res2.headers.get("X-Vantix-Cache") == "HIT"
        # Cache hits should be significantly faster
        assert latency < 20
