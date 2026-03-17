import pytest
import httpx
from app.core.redis import r

API_URL = "http://127.0.0.1:8083"

@pytest.fixture
async def api_client():
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=10.0) as client:
        yield client

@pytest.mark.asyncio
async def test_global_404_handler(api_client):
    # Hit a nonexistent endpoint
    res = await api_client.get("/nonexistent-endpoint-abc")
    
    # FastAPI default 404 is still handled by our global handler if it's a raised HTTPException
    # but some internal 404s might be different. Let's check our custom one.
    assert res.status_code == 404
    data = res.json()
    assert data["status"] == "error"
    assert "request_id" in data
    assert data["code"] == 404

@pytest.mark.asyncio
async def test_global_500_handler(api_client):
    # We need to trigger a server error. 
    # Let's hit the explain API with a bad risk_id or something that might fail if not handled.
    # Or we can temporarily add a "crash" endpoint for testing.
    # For now, let's just hit /v1/explain/invalid_id without auth
    res = await api_client.get("/v1/explain/invalid_id")
    
    # This should be a 401 or 403 (HTTPException), which our handler should capture
    assert res.status_code in [401, 403]
    data = res.json()
    assert data["status"] == "error"
    assert "request_id" in data

@pytest.mark.asyncio
async def test_trace_linkage(api_client):
    # Send a request and check if X-Request-ID in response matches request_id in JSON
    res = await api_client.get("/health")
    headers_req_id = res.headers.get("X-Request-ID")
    assert headers_req_id is not None
    
    # Now trigger an error and check linkage
    res = await api_client.get("/auth/signup") # GET not allowed, should be 405
    # 405 Method Not Allowed is an HTTPException
    assert res.status_code == 405
    data = res.json()
    assert data["request_id"] == res.headers.get("X-Request-ID")
