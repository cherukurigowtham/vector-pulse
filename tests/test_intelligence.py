import pytest
import httpx
from unittest.mock import patch, AsyncMock
from app.main import app
from app.core.security import require_api_key

@pytest.fixture
def auth_override():
    app.dependency_overrides[require_api_key] = lambda: {
        "email": "test@merchant.com",
        "key_hash": "test_hash",
        "data": {"plan": "growth"}
    }
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_fraud_ring_clustering(auth_override):
    """
    Test that 3 unique UIDs sharing a behavioral fingerprint triggers clustering.
    """
    # We mock the fingerprint SAD/SCARD logic to verify the threshold
    with patch("app.core.intelligence.r.scard", new_callable=AsyncMock) as mock_scard:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            order_data = {
                "uid": "unique_1",
                "amt": 1000,
                "addr": "123 Fraud Lane, Bangalore",
                "pin": "560102",
                "ip": "1.1.1.1"
            }
            
            # Case 1: First unique order (SCARD=1)
            mock_scard.return_value = 1
            res1 = await ac.post("/v1/risk-check", json=order_data)
            assert "FRAUD_RING_CLUSTER_DETECTED" not in res1.json()["risk_factors"]
            
            # Case 2: Third unique order (SCARD=3)
            mock_scard.return_value = 3
            res2 = await ac.post("/v1/risk-check", json=order_data)
            assert "FRAUD_RING_CLUSTER_DETECTED" in res2.json()["risk_factors"]
            assert res2.json()["risk_score"] >= 40.0

@pytest.mark.asyncio
async def test_neural_feedback_learning(auth_override):
    """
    Test that reporting RTO increases the weight of related risk factors.
    """
    with patch("app.core.redis.r.hgetall", new_callable=AsyncMock) as mock_hgetall, \
         patch("app.core.redis.r.hset", new_callable=AsyncMock) as mock_hset, \
         patch("app.core.redis.r.hget", new_callable=AsyncMock) as mock_hget, \
         patch("app.core.redis.r.get", new_callable=AsyncMock) as mock_get:
        
        # Setup mock for explain context
        mock_get.return_value = '{"flags": ["VELOCITY"], "score": 20}'
        mock_hget.return_value = 0.0 # Initial bias
        
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            # Report RTO for a transaction that had VELOCITY flag
            res = await ac.post("/v1/outcome", json={
                "risk_id": "test_risk_id",
                "status": "RTO"
            })
            assert res.status_code == 200
            # Since AUDIT_STORE.db is None in test, update_outcome returns gracefully.
            # verify hset was called to update the bias
            assert mock_hset.called
            # The bias bucket for testmerchant.com should be updated
            call_args = mock_hset.call_args_list[0]
            assert "neural:bias:test@merchant.com" in str(call_args)
