import pytest
import asyncio
from app.core.security import create_jwt_token, require_role
from fastapi import HTTPException, Request

class MockRequest:
    def __init__(self, token):
        self.cookies = {"vp_token": token}
        self.state = type('obj', (object,), {'user': None})

@pytest.mark.asyncio
async def test_rbac_permission_isolation():
    """
    Verifies that roles correctly restrict access to sensitive endpoints.
    """
    admin_token = create_jwt_token({"sub": "admin@vantix.ai", "role": "ADMIN", "team_id": "team_1"})
    analyst_token = create_jwt_token({"sub": "analyst@vantix.ai", "role": "ANALYST", "team_id": "team_1"})
    viewer_token = create_jwt_token({"sub": "viewer@vantix.ai", "role": "VIEWER", "team_id": "team_1"})

    # Test ADMIN requirement
    admin_dep = require_role(["ADMIN"])
    
    # 1. Admin should pass
    req_admin = MockRequest(admin_token)
    # Note: require_role is a dependency, in a real test we'd use TestClient, 
    # but here we simulate the logic.
    user = await admin_dep(req_admin)
    assert user["role"] == "ADMIN"

    # 2. Analyst should fail for ADMIN-only
    req_analyst = MockRequest(analyst_token)
    with pytest.raises(HTTPException) as excinfo:
        await admin_dep(req_analyst)
    assert excinfo.value.status_code == 403

    # 3. Viewer should fail for ADMIN-only
    req_viewer = MockRequest(viewer_token)
    with pytest.raises(HTTPException) as excinfo:
        await admin_dep(req_viewer)
    assert excinfo.value.status_code == 403

@pytest.mark.asyncio
async def test_team_isolation_logic():
    """
    Verifies that team_id is correctly extracted and present in the session.
    """
    token = create_jwt_token({"sub": "user@corp.com", "role": "ANALYST", "team_id": "alpha_team"})
    req = MockRequest(token)
    
    dep = require_role(["ADMIN", "ANALYST", "VIEWER"])
    user = await dep(req)
    
    assert user["team_id"] == "alpha_team"
    assert user["email"] == "user@corp.com"
