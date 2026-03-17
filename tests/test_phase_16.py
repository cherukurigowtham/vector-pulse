import pytest
import hmac
import hashlib
import time
import json
import base64
import httpx
from app.main import app
from app.core.redis import r
from app.core.signal_tunnel import tunnel

@pytest.fixture(autouse=True)
async def setup_api_keys():
    # Inject keys for all tests
    keys = {
        "success_key": "enterprise_success@merchant.com",
        "fail_key": "enterprise_fail@merchant.com",
        "replay_key": "enterprise_replay@merchant.com"
    }
    hashes = []
    for k, email in keys.items():
        kh = hashlib.sha256(k.encode()).hexdigest()
        await r.hset(f"apikey:{kh}", mapping={
            "email": email,
            "plan": "growth",
            "secret": k
        })
        hashes.append(f"apikey:{kh}")
    
    yield
    
    for h in hashes:
        await r.delete(h)
    async for key in r.scan_iter("nonce:*"):
        await r.delete(key)

@pytest.mark.asyncio
async def test_iron_shield_signature_success():
    """Verify that a correctly signed behavioral ingestion is accepted."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        nonce = "success_nonce"
        timestamp = str(int(time.time()))
        body = {"payload": tunnel.encrypt_signal({"session_id": "session_signed_123456789", "events": []})}
        raw_json_body = json.dumps(body, separators=(',', ':')).encode()
        
        message = nonce.encode() + timestamp.encode() + raw_json_body
        signature = hmac.new(b"success_key", message, hashlib.sha256).hexdigest()
        
        res = await ac.post("/v1/behavioral/ingest", 
            content=raw_json_body,
            headers={
                "X-API-Key": "success_key",
                "X-Vantix-Signature": signature,
                "X-Vantix-Nonce": nonce,
                "X-Vantix-Timestamp": timestamp,
                "Content-Type": "application/json"
            }
        )
        assert res.status_code == 200

@pytest.mark.asyncio
async def test_iron_shield_signature_fail():
    """Verify that an incorrectly signed request is rejected."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/v1/behavioral/ingest", 
            json={"payload": "invalid"},
            headers={
                "X-API-Key": "fail_key",
                "X-Vantix-Signature": "wrong_sig",
                "X-Vantix-Nonce": "n",
                "X-Vantix-Timestamp": str(int(time.time()))
            }
        )
        assert res.status_code == 403
        assert "Invalid X-Vantix-Signature" in res.json()["message"]

@pytest.mark.asyncio
async def test_iron_shield_replay_protection():
    """Verify that a nonce cannot be reused."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        nonce = "replay_nonce_fixed"
        timestamp = str(int(time.time()))
        body = {"payload": tunnel.encrypt_signal({"session_id": "session_signed_123456789", "events": []})}
        raw_json_body = json.dumps(body, separators=(',', ':')).encode()
        
        message = nonce.encode() + timestamp.encode() + raw_json_body
        signature = hmac.new(b"replay_key", message, hashlib.sha256).hexdigest()
        
        headers = {
            "X-API-Key": "replay_key",
            "X-Vantix-Signature": signature,
            "X-Vantix-Nonce": nonce,
            "X-Vantix-Timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        res1 = await ac.post("/v1/behavioral/ingest", content=raw_json_body, headers=headers)
        assert res1.status_code == 200
        
        res2 = await ac.post("/v1/behavioral/ingest", content=raw_json_body, headers=headers)
        assert res2.status_code == 403
        assert "Replay attack detected" in res2.json()["message"]
