import pytest
import httpx
from app.main import app
from app.core.security import create_jwt_token

BASE_URL = "http://testserver"

@pytest.fixture
async def async_client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
        yield client

def get_auth_cookies(role: str = "ADMIN", team_id: str = "team_1"):
    token = create_jwt_token({"sub": f"test_{role.lower()}@vantix.ai", "role": role, "team_id": team_id})
    return {"vp_token": token}

@pytest.mark.asyncio
async def test_extreme_numerical_orders(async_client):
    """Test the risk engine with extreme numerical values."""
    payload = {
        "uid": "u_extreme_1",
        "amt": 999999999.99,
        "addr": "123 Extreme Heights, Mumbai",
        "pin": "400001",
        "name": "Rich Fraudster",
        "email": "rich@fraud.com",
        "phone": "9876543210",
        "ip": "1.1.1.1",
        "device_hash": "device_1234567890abcdef",
        "card_bin": "411111"
    }
    # Use Admin Key bypass
    headers = {"X-Admin-Key": "local-dev-admin-key"}
    res = await async_client.post("/api/v1/risk/scan", json=payload, headers=headers)
    assert res.status_code == 200
    assert "score" in res.json()

@pytest.mark.asyncio
async def test_rbac_cross_team_isolation(async_client):
    """Test that a user cannot access data from another team."""
    alpha_cookies = get_auth_cookies(role="ADMIN", team_id="team_alpha")
    beta_cookies = get_auth_cookies(role="ADMIN", team_id="team_beta")

    # Invite to Team Alpha
    await async_client.post("/v1/team/invite?email=new@alpha.com&role=ANALYST", cookies=alpha_cookies)

    # Team Beta should NOT see Alpha's invites
    res = await async_client.get("/v1/team/invites", cookies=beta_cookies)
    assert res.status_code == 200
    invites = res.json()
    for invite in invites:
        assert invite["email"] != "new@alpha.com"

@pytest.mark.asyncio
async def test_malformed_string_injection(async_client):
    """Test against Unicode injection and control characters."""
    headers = {"X-Admin-Key": "local-dev-admin-key"}
    payload = {
        "uid": "u_inject_1",
        "amt": 100.0,
        "addr": "123 Place \u202e mal \u202d safe \n\r\t", 
        "pin": "123456",
        "name": "Injection Test \x00\x01\x02",
        "ip": "127.0.0.1",
        "device_hash": "device_1234567890abcdef",
        "card_bin": "123456"
    }
    res = await async_client.post("/api/v1/risk/scan", json=payload, headers=headers)
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_unauthenticated_access_to_merchant_routes(async_client):
    """Ensures that without token/session, merchant routes are strictly unreachable."""
    routes = [
        "/v1/auth/me",
        "/v1/team/members",
        "/v1/auth/settings"
    ]
    for route in routes:
        res = await async_client.get(route)
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_invalid_json_payloads(async_client):
    """Test the robustness of JSON parsing."""
    headers = {"X-Admin-Key": "local-dev-admin-key", "Content-Type": "application/json"}
    res = await async_client.post(
        "/api/v1/risk/scan", 
        content='{"uid": "test", "amt": 10.0', 
        headers=headers
    )
    assert res.status_code in [400, 422]

if __name__ == "__main__":
    # If run directly, run the tests
    pytest.main([__file__])
