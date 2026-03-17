import pytest
import httpx
from app.main import app
from app.core.redis import r

from unittest.mock import patch, AsyncMock

@pytest.fixture
def auth_client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

@pytest.mark.asyncio
@patch("app.routers.public._sliding_window_rate_limit", new_callable=AsyncMock)
async def test_auth_lifecycle(mock_limit, auth_client):
    mock_limit.return_value = False
    email = f"merchant_{int(time.time())}@test.com"
    password = "StrongPassword123!"
    
    # 1. Signup
    async with auth_client as ac:
        res = await ac.post("/auth/signup", json={"email": email, "password": password})
        assert res.status_code == 200
        assert "api_key" in res.json()
        
        # 2. Duplicate Signup
        res = await ac.post("/auth/signup", json={"email": email, "password": password})
        assert res.status_code == 400
        
        # 3. Login
        res = await ac.post("/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200
        assert "vp_session" in res.cookies
        
        # 4. Forgot Password
        res = await ac.post("/auth/forgot-password", json={"email": email})
        assert res.status_code == 200
        token = res.json().get("debug_token")
        assert token is not None
        
        # 5. Reset Password
        new_password = "EvenStrongerPassword456!"
        res = await ac.post("/auth/reset-password", json={"token": token, "new_password": new_password})
        assert res.status_code == 200
        
        # 6. Login with Old Password (Should Fail)
        res = await ac.post("/auth/login", json={"email": email, "password": password})
        assert res.status_code == 401
        
        # 7. Login with New Password
        res = await ac.post("/auth/login", json={"email": email, "password": new_password})
        assert res.status_code == 200
        
        # 8. Invalid Token Reset
        res = await ac.post("/auth/reset-password", json={"token": "fake", "new_password": "ValidPassword123"})
        assert res.status_code == 400

@pytest.mark.asyncio
@patch("app.routers.public._sliding_window_rate_limit", new_callable=AsyncMock)
async def test_auth_security_constraints(mock_limit, auth_client):
    mock_limit.return_value = False
    async with auth_client as ac:
        # Invalid email format
        res = await ac.post("/auth/signup", json={"email": "invalid-email", "password": "short"})
        assert res.status_code == 422
        
        # Admin identity reservation (Checking for default admin email)
        res = await ac.post("/auth/signup", json={"email": "admin@vantix.ai", "password": "SomePassword123"})
        assert res.status_code == 403

import time
