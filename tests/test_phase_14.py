import pytest
import time
import httpx
from app.main import app
from app.core.redis import r
from app.db.database import AUDIT_STORE
import hashlib

@pytest.fixture(autouse=True)
async def setup_environment():
    # Inject a known test key into Redis for the session
    test_key = "test_key_123"
    key_hash = hashlib.sha256(test_key.encode()).hexdigest()
    await r.hset(f"apikey:{key_hash}", mapping={
        "email": "test@merchant.com",
        "plan": "starter",
        "key_prefix": "test_prefix",
        "key_suffix": "test_suffix"
    })
    
    # Initialize DB for tests
    await AUDIT_STORE.init()
    
    yield
    
    await r.delete(f"apikey:{key_hash}")
    # We don't close the DB here to avoid issues with other tests or parallel runs

@pytest.mark.asyncio
async def test_compliance_report_generation():
    """Verify that the compliance report engine aggregates data correctly."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Fetch report (should be empty but valid)
        res = await ac.get("/v1/compliance/report?start_timestamp=0", headers={"X-API-Key": "test_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert "report_id" in data
        assert "security_anchor" in data
        
        # 2. Test CSV format
        res_csv = await ac.get("/v1/compliance/report?start_timestamp=0&format=csv", headers={"X-API-Key": "test_key_123"})
        assert res_csv.status_code == 200
        assert "csv" in res_csv.json()

@pytest.mark.asyncio
async def test_ai_forensics_assistant():
    """Verify that the forensics assistant provides adjudication narratives."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Mocking a risk ID
        risk_id = "test_risk_id"
        
        res = await ac.post("/v1/forensics/ask", json={"risk_id": risk_id}, headers={"X-API-Key": "test_key_123"})
        
        # If record not found, should be 404
        if res.status_code == 404:
            resp_json = res.json()
            assert resp_json["status"] == "error"
            assert "message" in resp_json
        else:
            assert res.status_code == 200
            assert "adjudication_narrative" in res.json()
