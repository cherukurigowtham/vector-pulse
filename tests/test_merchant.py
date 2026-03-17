import unittest
import pytest
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
import json
import time
import hashlib
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock vector_pulse before it gets imported by app modules
mock_vp = MagicMock()
mock_vp.is_gibberish_address.return_value = False
mock_vp.is_suspicious_name.return_value = False
mock_vp.is_suspicious_phone.return_value = False
mock_vp.is_email_name_mismatch.return_value = False
mock_vp.has_poor_address_structure.return_value = False
sys.modules["vector_pulse"] = mock_vp

from app.main import app
from app.core.security import require_api_key

# Target usage sites for patching
@pytest.fixture
def mock_r():
    with patch("app.routers.merchant.r", new_callable=AsyncMock) as m:
        yield m

@pytest.fixture
def mock_audit():
    with patch("app.core.helpers.AUDIT_STORE", new_callable=AsyncMock) as m1:
        with patch("app.routers.merchant.AUDIT_STORE", new_callable=AsyncMock) as m2:
            # Set default return values to avoid RecursionError during JSON serialization
            m1.fetch_recent_risk_audits.return_value = []
            m2.fetch_recent_risk_audits.return_value = []
            m2.fetch_risk_profile_audits.return_value = []
            yield m1, m2

@pytest.fixture
def auth_override():
    test_email = "merchant@test.com"
    mock_merchant = {
        "email": test_email,
        "key_hash": "mock_hash",
        "data": {
            "email": test_email,
            "plan": "starter",
            "risk_decision_threshold": "50"
        }
    }
    app.dependency_overrides[require_api_key] = lambda: mock_merchant
    yield mock_merchant
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_config_success(auth_override, mock_r, mock_audit):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/merchant/config", headers={"X-API-Key": "vp_test"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == auth_override["email"]
        assert data["risk_config"]["decision_threshold"] == 50

@pytest.mark.asyncio
async def test_get_config_invalid_key(mock_r, mock_audit):
    # Override with failure
    def fail(): raise HTTPException(status_code=403, detail="Invalid API key")
    app.dependency_overrides[require_api_key] = fail
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/merchant/config", headers={"X-API-Key": "invalid"})
        assert response.status_code == 403
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_update_config_success(auth_override, mock_r, mock_audit):
    mock_r.hgetall.return_value = {
        "email": auth_override["email"], 
        "plan": "starter", 
        "risk_decision_threshold": "85"
    }
    
    update_data = {"decision_threshold": 85}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/merchant/config", 
            headers={"X-API-Key": "vp_test"},
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["risk_config"]["decision_threshold"] == 85
        mock_r.hset.assert_called()

@pytest.mark.asyncio
async def test_get_stats_success(auth_override, mock_r, mock_audit):
    mock_r.get.side_effect = [
        "150", # usage_this_month
        "10",  # total_blocks
        "5000" # total_savings
    ]
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/merchant/stats", headers={"X-API-Key": "vp_test"})
        assert response.status_code == 200
        data = response.json()
        assert data["total_blocks"] == 10
        assert data["total_savings_inr"] == 5000
        assert data["usage_this_month"] == 150
