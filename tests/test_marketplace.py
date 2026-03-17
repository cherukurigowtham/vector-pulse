import pytest
import httpx
import json
import asyncio
from app.main import app
from app.core.redis import r

@pytest.fixture(autouse=True)
async def clean_redis():
    yield
    # Cleanup after each test
    async for key in r.scan_iter("merchant:test_marketplace@merchant.com:apps"):
        await r.delete(key)

@pytest.mark.asyncio
async def test_marketplace_app_lifecycle():
    """Verify listing, installing, and uninstalling apps."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"X-API-Key": "test_marketplace_key"}
        # Inject test key
        import hashlib
        kh = hashlib.sha256(b"test_marketplace_key").hexdigest()
        await r.hset(f"apikey:{kh}", mapping={"email": "test_marketplace@merchant.com", "secret": "s"})
        
        # 1. List available apps
        res = await ac.get("/v1/marketplace/apps", headers=headers)
        assert res.status_code == 200
        apps = res.json()["apps"]
        assert len(apps) >= 3
        # Check initial state
        assert not any(app["is_installed"] for app in apps)
        
        # 2. Install an app
        app_id = apps[0]["id"]
        res = await ac.post(f"/v1/marketplace/install/{app_id}", headers=headers)
        assert res.status_code == 200
        assert "installed successfully" in res.json()["message"]
        
        # 3. Verify it's listed as installed
        res = await ac.get("/v1/marketplace/apps", headers=headers)
        apps_after = res.json()["apps"]
        installed_app = next(a for a in apps_after if a["id"] == app_id)
        assert installed_app["is_installed"] is True
        
        # 4. Uninstall the app
        res = await ac.delete(f"/v1/marketplace/uninstall/{app_id}", headers=headers)
        assert res.status_code == 200
        
        # 5. Verify it's uninstalled
        res = await ac.get("/v1/marketplace/apps", headers=headers)
        apps_final = res.json()["apps"]
        uninstalled_app = next(a for a in apps_final if a["id"] == app_id)
        assert uninstalled_app["is_installed"] is False

@pytest.mark.asyncio
async def test_plugin_integration_in_risk_analysis():
    """Verify that installed plugins contribute to the risk score."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"X-API-Key": "test_plugin_key"}
        email = "test_plugin@merchant.com"
        import hashlib
        kh = hashlib.sha256(b"test_plugin_key").hexdigest()
        await r.hset(f"apikey:{kh}", "email", email)
        await r.hset(f"apikey:{kh}", "secret", "s")
        await r.hset(f"apikey:{kh}", "plan", "growth")
        
        # Install 'bot_shield_pro'
        await ac.post("/v1/marketplace/install/bot_shield_pro", headers=headers)
        
        # Run risk analysis with a payload that triggers Bot-Shield (short uid)
        payload = {
            "uid": "short", 
            "amt": 1000,
            "addr": "123 Test St, Mumbai",
            "ip": "127.0.0.1",
            "name": "Marketplace Tester",
            "email": "tester@example.com",
            "phone": "9999999999",
            "pin": "400001"
        }
        
        res = await ac.post("/v1/risk-check", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        
        # Check if plugin impact is present in XAI
        assert "MARKETPLACE_BOT_SHIELD_PRO" in data["impact_analysis"]
        assert any("BOT_SHIELD_PRO" in flag for flag in data["risk_factors"])
        
        # Verify the score contribution
        # Bot Shield Pro has base_weight 0.25 and triggers 0.85 for short uid -> 0.21 approx impact
        assert data["impact_analysis"]["MARKETPLACE_BOT_SHIELD_PRO"] > 0
