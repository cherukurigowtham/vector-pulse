import os
import time

import httpx
import pytest
import redis.asyncio as redis

from api_gateway import _hash_key


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
API_URL = os.getenv("VECTOR_PULSE_API_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "local-dev-admin-key")


@pytest.fixture(scope="function")
async def r_client():
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    yield client
    await client.aclose()


@pytest.fixture(scope="function")
async def api_client():
    async with httpx.AsyncClient(base_url=API_URL, timeout=10.0) as client:
        yield client


@pytest.mark.asyncio
async def test_live_redis_connectivity(r_client):
    assert await r_client.ping() is True


@pytest.mark.asyncio
async def test_live_health_reports_dependencies(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "redis" in payload
    assert "audit" in payload
    assert "audit_backend" in payload


@pytest.mark.asyncio
async def test_live_registration_and_flow(r_client, api_client):
    email = f"test_{int(time.time())}@example.com"
    reg_res = await api_client.post(
        "/v1/register",
        json={
            "email": email,
            "plan": "starter",
            "admin_key": ADMIN_KEY,
        },
    )
    assert reg_res.status_code == 200
    api_key = reg_res.json()["api_key"]

    risk_res = await api_client.post(
        "/v1/risk-check",
        headers={"X-API-Key": api_key},
        json={
            "uid": f"user_integration_{int(time.time())}",
            "amt": 4500,
            "addr": "Bangalore Central",
            "pin": "560001",
            "ip": "1.1.1.1",
        },
    )
    assert risk_res.status_code == 200
    data = risk_res.json()
    assert "decision" in data
    assert "risk_score" in data
    assert "risk_id" in data

    key_hash = _hash_key(api_key)
    stored_email = await r_client.hget(f"apikey:{key_hash}", "email")
    assert stored_email == email

    cached_explain = await r_client.get(f"explain:{data['risk_id']}")
    assert cached_explain is not None


@pytest.mark.asyncio
async def test_admin_access_live(api_client):
    sess_res = await api_client.post(
        "/v1/admin/session",
        json={"admin_key": ADMIN_KEY},
    )
    assert sess_res.status_code == 200

    users_res = await api_client.get("/v1/admin/users")
    assert users_res.status_code == 200
    assert "users" in users_res.json()


@pytest.mark.asyncio
async def test_live_outcome_update(api_client):
    email = f"outcome_{int(time.time())}@example.com"
    reg_res = await api_client.post(
        "/v1/register",
        json={
            "email": email,
            "plan": "starter",
            "admin_key": ADMIN_KEY,
        },
    )
    assert reg_res.status_code == 200
    api_key = reg_res.json()["api_key"]

    risk_res = await api_client.post(
        "/v1/risk-check",
        headers={"X-API-Key": api_key},
        json={
            "uid": f"user_outcome_{int(time.time())}",
            "amt": 3200,
            "addr": "HSR Layout",
            "pin": "560102",
            "ip": "1.1.1.1",
        },
    )
    assert risk_res.status_code == 200
    risk_id = risk_res.json()["risk_id"]

    outcome_res = await api_client.post(
        "/v1/outcome",
        headers={"X-API-Key": api_key},
        json={"risk_id": risk_id, "status": "DELIVERED"},
    )
    assert outcome_res.status_code == 200
    assert outcome_res.json()["updated_to"] == "DELIVERED"
