import pytest
import httpx
from app.main import app
from app.core.security import require_admin

@pytest.fixture
def admin_override():
    app.dependency_overrides[require_admin] = lambda: "admin@vectorpulse.com"
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_admin_dashboard_stats(admin_override):
    from unittest.mock import patch, AsyncMock
    with patch("app.routers.admin_dashboard.r.mget", new_callable=AsyncMock) as mock_mget:
        # Mock Redis data
        mock_mget.return_value = [b"15000", b"100", b"30", b"20", b"10", b"5", b"35"]
        
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/v1/admin/dashboard")
            assert res.status_code == 200
            data = res.json()
            
            assert data["financial_impact"]["total_savings_inr"] == 15000
            assert data["operational_metrics"]["total_prevented_frauds"] == 100
            assert data["operational_metrics"]["risk_vector_distribution"]["velocity_spikes"] == 30
            assert data["system_health"]["engine_status"] == "OPERATIONAL"

@pytest.mark.asyncio
async def test_admin_dashboard_unauthorized():
    # No override means require_admin will fail (or use default which checks session)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/v1/admin/dashboard")
        assert res.status_code == 403 # Should fail with Forbidden if no session/overrides
