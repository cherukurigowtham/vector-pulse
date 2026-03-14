import importlib
import json
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


class FakeGeoReader:
    def get(self, ip):
        return None


class FakeAioSQLiteConnection:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, *args, **kwargs):
        return self

    async def commit(self):
        return None


class FakePipeline:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.ops = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def zadd(self, key, mapping):
        self.ops.append(("zadd", key, mapping))

    def zremrangebyscore(self, key, start, end):
        self.ops.append(("zremrangebyscore", key, start, end))

    def zcard(self, key):
        self.ops.append(("zcard", key))

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))

    def scard(self, key):
        self.ops.append(("scard", key))

    def incr(self, key):
        self.ops.append(("incr", key))

    def incrby(self, key, amount):
        self.ops.append(("incrby", key, amount))

    def setex(self, key, ttl, value):
        self.ops.append(("setex", key, ttl, value))

    def set(self, key, value):
        self.ops.append(("set", key, value))

    def hset(self, key, mapping):
        self.ops.append(("hset", key, mapping))

    def hdel(self, key, field):
        self.ops.append(("hdel", key, field))

    def sadd(self, key, value):
        self.ops.append(("sadd", key, value))

    def srem(self, key, value):
        self.ops.append(("srem", key, value))

    def delete(self, key):
        self.ops.append(("delete", key))

    def get(self, key):
        self.ops.append(("get", key))

    def hgetall(self, key):
        self.ops.append(("hgetall", key))

    def lrange(self, key, start, end):
        self.ops.append(("lrange", key, start, end))

    def lpush(self, key, value):
        self.ops.append(("lpush", key, value))

    def ltrim(self, key, start, end):
        self.ops.append(("ltrim", key, start, end))

    async def execute(self):
        results = []
        for op in self.ops:
            name = op[0]
            if name == "incr":
                results.append(await self.redis_client.incr(op[1]))
            elif name == "setex":
                results.append(await self.redis_client.setex(op[1], op[2], op[3]))
            elif name == "set":
                results.append(await self.redis_client.set(op[1], op[2]))
            elif name == "incrby":
                results.append(await self.redis_client.incrby(op[1], op[2]))
            elif name == "hset":
                results.append(await self.redis_client.hset(op[1], op[2]))
            elif name == "hdel":
                results.append(await self.redis_client.hdel(op[1], op[2]))
            elif name == "sadd":
                results.append(await self.redis_client.sadd(op[1], op[2]))
            elif name == "srem":
                results.append(await self.redis_client.srem(op[1], op[2]))
            elif name == "delete":
                results.append(await self.redis_client.delete(op[1]))
            elif name == "get":
                results.append(await self.redis_client.get(op[1]))
            elif name == "hgetall":
                results.append(await self.redis_client.hgetall(op[1]))
            elif name == "lrange":
                results.append(await self.redis_client.lrange(op[1], op[2], op[3]))
            elif name == "lpush":
                results.append(await self.redis_client.lpush(op[1], op[2]))
            elif name == "ltrim":
                results.append(await self.redis_client.ltrim(op[1], op[2], op[3]))
            elif name == "scard":
                results.append(await self.redis_client.scard(op[1]))
            elif name == "sismember":
                results.append(await self.redis_client.sismember(op[1], op[2]))
            else:
                results.append(0)
        self.ops.clear()
        return results


class FakeRedis:
    def __init__(self):
        self.strings = {}
        self.hashes = {}
        self.sets = {}
        self.lists = {}

    async def get(self, key):
        return self.strings.get(key)

    async def setex(self, key, ttl, value):
        self.strings[key] = value
        return True

    async def set(self, key, value):
        self.strings[key] = value
        return True

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def hset(self, key, mapping):
        existing = self.hashes.setdefault(key, {})
        existing.update(mapping)
        return True

    async def hdel(self, key, field):
        existing = self.hashes.get(key, {})
        existed = field in existing
        existing.pop(field, None)
        return 1 if existed else 0

    async def smembers(self, key):
        return set(self.sets.get(key, set()))

    async def scard(self, key):
        return len(self.sets.get(key, set()))

    async def sismember(self, key, value):
        return value in self.sets.get(key, set())

    async def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(value)
        return True

    async def srem(self, key, value):
        self.sets.setdefault(key, set()).discard(value)
        return True

    async def lrange(self, key, start, end):
        values = self.lists.get(key, [])
        if end == -1:
            return list(values[start:])
        return list(values[start:end + 1])

    async def lpush(self, key, value):
        values = self.lists.setdefault(key, [])
        values.insert(0, value)
        return len(values)

    async def ltrim(self, key, start, end):
        values = self.lists.get(key, [])
        if end == -1:
            self.lists[key] = values[start:]
        else:
            self.lists[key] = values[start:end + 1]
        return True

    async def delete(self, key):
        self.strings.pop(key, None)
        self.hashes.pop(key, None)
        self.sets.pop(key, None)
        self.lists.pop(key, None)
        return True

    async def incr(self, key):
        current = int(self.strings.get(key, 0))
        current += 1
        self.strings[key] = str(current)
        return current

    async def incrby(self, key, amount):
        current = int(self.strings.get(key, 0))
        current += amount
        self.strings[key] = str(current)
        return current

    async def ping(self):
        return True

    def pipeline(self):
        return FakePipeline(self)


def load_app_module():
    class StubRedisModule:
        class Redis:
            def __init__(self, *args, **kwargs):
                pass

    fake_vector_pulse = types.SimpleNamespace(
        calculate_stats=lambda data: (0.0, 0.0),
        is_anomaly_sigma=lambda current, avg, std_dev, threshold: False,
        detect_amount_anomaly=lambda history, current, threshold: (False, 0.0, 0.0),
        calculate_trust_score=lambda delivered, total: 50.0 if total == 0 else (delivered / total) * 100.0,
        evaluate_weighted_risk=lambda velocity, sybil, anomaly, trust, vpn: 0.0,
        normalize_address=lambda addr: addr.lower().strip(),
        address_fingerprint=lambda addr: addr.lower().strip(),
        address_match_score=lambda left, right: 0.0,
    )
    fake_aiosqlite = types.SimpleNamespace(connect=lambda *args, **kwargs: FakeAioSQLiteConnection())
    fake_geolite2 = types.SimpleNamespace(geolite2=types.SimpleNamespace(reader=lambda: FakeGeoReader()))
    fake_redis_asyncio = StubRedisModule()
    fake_redis = types.SimpleNamespace(asyncio=fake_redis_asyncio)

    with patch.dict(
        sys.modules,
        {
            "vector_pulse": fake_vector_pulse,
            "aiosqlite": fake_aiosqlite,
            "geolite2": fake_geolite2,
            "redis": fake_redis,
            "redis.asyncio": fake_redis_asyncio,
        },
    ):
        sys.modules.pop("api_gateway", None)
        return importlib.import_module("api_gateway")


class ApiGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_app_module()
        cls.redis = FakeRedis()
        cls.module.r = cls.redis
        from fastapi.testclient import TestClient

        cls.client = TestClient(cls.module.app)

    def setUp(self):
        self.redis.strings.clear()
        self.redis.hashes.clear()
        self.redis.sets.clear()
        self.redis.lists.clear()
        self.client.cookies.clear()

    def test_public_request_free_key_creates_key_profile(self):
        response = self.client.post(
            "/v1/public/request-free-key",
            json={"email": "user@example.com"},
            headers={"X-Forwarded-For": "1.2.3.4"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["plan"], "free")
        self.assertTrue(payload["api_key"].startswith("vp_"))

        stored_keys = list(self.redis.hashes.keys())
        self.assertEqual(len(stored_keys), 1)
        self.assertEqual(self.redis.hashes[stored_keys[0]]["email"], "user@example.com")
        self.assertNotIn("api_key", self.redis.hashes[stored_keys[0]])

    def test_public_request_pilot_persists_lead(self):
        with patch.object(self.module, "_send_pilot_request_webhook", new=AsyncMock()) as webhook_mock:
            response = self.client.post(
                "/v1/public/request-pilot",
                json={
                    "name": "Asha",
                    "email": "asha@example.com",
                    "company": "Pilot Store",
                    "category": "Beauty",
                    "monthly_orders": "5000-10000",
                    "cod_share": "40-60%",
                },
                headers={"X-Forwarded-For": "1.2.3.4"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(
            self.redis.hashes["pilot_request:asha@example.com"]["company"],
            "Pilot Store",
        )
        self.assertEqual(
            self.redis.hashes["pilot_request:asha@example.com"]["status"],
            "new",
        )
        self.assertIn("asha@example.com", self.redis.sets["pilot_request_emails"])
        self.assertTrue(self.redis.lists["pilot_requests"])
        webhook_mock.assert_awaited_once()

    def test_admin_can_list_pilot_requests(self):
        self.redis.sets["pilot_request_emails"] = {"asha@example.com"}
        self.redis.hashes["pilot_request:asha@example.com"] = {
            "name": "Asha",
            "email": "asha@example.com",
            "company": "Pilot Store",
            "category": "Beauty",
            "monthly_orders": "5000-10000",
            "cod_share": "40-60%",
            "status": "new",
            "submitted_at": "1710000000.0",
            "source": "landing_page",
            "ip": "1.2.3.4",
        }

        response = self.client.get(
            "/v1/admin/pilot-requests",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["requests"][0]["company"], "Pilot Store")

    def test_admin_can_update_pilot_request_status(self):
        self.redis.sets["pilot_request_emails"] = {"asha@example.com"}
        self.redis.hashes["pilot_request:asha@example.com"] = {
            "name": "Asha",
            "email": "asha@example.com",
            "company": "Pilot Store",
            "category": "Beauty",
            "monthly_orders": "5000-10000",
            "cod_share": "40-60%",
            "status": "new",
            "submitted_at": "1710000000.0",
            "source": "landing_page",
            "ip": "1.2.3.4",
        }

        response = self.client.post(
            "/v1/admin/pilot-requests/asha@example.com/status",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
            json={"status": "contacted"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(
            self.redis.hashes["pilot_request:asha@example.com"]["status"],
            "contacted",
        )

    def test_admin_can_update_pilot_request_details(self):
        self.redis.sets["pilot_request_emails"] = {"asha@example.com"}
        self.redis.hashes["pilot_request:asha@example.com"] = {
            "name": "Asha",
            "email": "asha@example.com",
            "company": "Pilot Store",
            "category": "Beauty",
            "monthly_orders": "5000-10000",
            "cod_share": "40-60%",
            "status": "new",
            "assigned_to": "",
            "notes": "",
            "submitted_at": "1710000000.0",
            "source": "landing_page",
            "ip": "1.2.3.4",
        }

        response = self.client.post(
            "/v1/admin/pilot-requests/asha@example.com/details",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
            json={"assigned_to": "gowtham", "notes": "High COD share. Reach out on Monday."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.redis.hashes["pilot_request:asha@example.com"]["assigned_to"],
            "gowtham",
        )
        self.assertEqual(
            self.redis.hashes["pilot_request:asha@example.com"]["notes"],
            "High COD share. Reach out on Monday.",
        )

    def test_admin_can_get_pilot_analytics(self):
        self.redis.sets["pilot_request_emails"] = {"asha@example.com", "vivek@example.com"}
        self.redis.hashes["pilot_request:asha@example.com"] = {
            "name": "Asha",
            "email": "asha@example.com",
            "company": "Pilot Store",
            "category": "Beauty",
            "monthly_orders": "5000-10000",
            "cod_share": "40-60%",
            "status": "won",
            "assigned_to": "gowtham",
            "submitted_at": "1710000000.0",
        }
        self.redis.hashes["pilot_request:vivek@example.com"] = {
            "name": "Vivek",
            "email": "vivek@example.com",
            "company": "Trend Cart",
            "category": "Fashion",
            "monthly_orders": "1000-5000",
            "cod_share": "60-80%",
            "status": "contacted",
            "assigned_to": "",
            "submitted_at": "1710001000.0",
        }

        response = self.client.get(
            "/v1/admin/pilot-analytics",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["funnel"]["won"], 1)
        self.assertEqual(payload["funnel"]["contacted"], 1)
        self.assertEqual(payload["funnel"]["conversion_rate"], 50.0)
        self.assertEqual(payload["top_categories"][0]["count"], 1)

    def test_admin_can_list_upgrade_requests(self):
        self.redis.sets["upgrade_request_emails"] = {"user@example.com"}
        self.redis.hashes["upgrade_request:user@example.com"] = {
            "email": "user@example.com",
            "current_plan": "free",
            "requested_plan": "growth",
            "note": "Need higher monthly volume.",
            "status": "submitted",
            "submitted_at": "1710000000.0",
        }

        response = self.client.get(
            "/v1/admin/upgrade-requests",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["requests"][0]["requested_plan"], "growth")

    def test_admin_can_approve_upgrade_request_and_update_plan(self):
        self.redis.sets["upgrade_request_emails"] = {"user@example.com"}
        self.redis.hashes["upgrade_request:user@example.com"] = {
            "email": "user@example.com",
            "current_plan": "free",
            "requested_plan": "growth",
            "note": "Need higher monthly volume.",
            "status": "submitted",
            "submitted_at": "1710000000.0",
        }
        self.redis.hashes["user:user@example.com"] = {"plan": "free"}
        self.redis.hashes["apikey:hash_123"] = {"email": "user@example.com", "plan": "free"}
        self.redis.strings["emailkey:user@example.com"] = "hash_123"

        response = self.client.post(
            "/v1/admin/upgrade-requests/user@example.com/status",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.redis.hashes["upgrade_request:user@example.com"]["status"], "approved")
        self.assertEqual(self.redis.hashes["user:user@example.com"]["plan"], "growth")
        self.assertEqual(self.redis.hashes["apikey:hash_123"]["plan"], "growth")

    def test_admin_can_reject_upgrade_request_without_changing_plan(self):
        self.redis.sets["upgrade_request_emails"] = {"user@example.com"}
        self.redis.hashes["upgrade_request:user@example.com"] = {
            "email": "user@example.com",
            "current_plan": "free",
            "requested_plan": "growth",
            "note": "Need higher monthly volume.",
            "status": "submitted",
            "submitted_at": "1710000000.0",
        }
        self.redis.hashes["user:user@example.com"] = {"plan": "free"}
        self.redis.hashes["apikey:hash_123"] = {"email": "user@example.com", "plan": "free"}
        self.redis.strings["emailkey:user@example.com"] = "hash_123"

        response = self.client.post(
            "/v1/admin/upgrade-requests/user@example.com/status",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
            json={"status": "rejected"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.redis.hashes["upgrade_request:user@example.com"]["status"], "rejected")
        self.assertEqual(self.redis.hashes["user:user@example.com"]["plan"], "free")
        self.assertEqual(self.redis.hashes["apikey:hash_123"]["plan"], "free")

    def test_admin_users_returns_dashboard_fields(self):
        self.redis.sets["admin:all_keys"] = {"hash_1"}
        self.redis.hashes["apikey:hash_1"] = {
            "email": "client@example.com",
            "plan": "starter",
            "key_prefix": "vp_demo1",
            "key_suffix": "1234",
            "created_at": "2026-03-13T00:00:00Z",
        }
        self.redis.strings["usage:hash_1:2026-03"] = "12"
        self.redis.strings["total_savings_inr"] = "280"
        self.redis.lists["recent_blocks"] = ["u1: HIGH_VELOCITY [ID: abc123]"]

        with patch.object(self.module.time, "strftime", return_value="2026-03"):
            response = self.client.get("/v1/admin/users", headers={"X-Admin-Key": self.module.ADMIN_KEY})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_users"], 1)
        self.assertEqual(payload["savings"], 280)
        self.assertEqual(payload["recent_blocks"], ["u1: HIGH_VELOCITY [ID: abc123]"])
        self.assertEqual(payload["users"][0]["api_key_preview"], "vp_demo1...1234")

    def test_admin_business_metrics_returns_operating_summary(self):
        self.redis.sets["admin:all_keys"] = {"hash_1", "hash_2"}
        self.redis.hashes["apikey:hash_1"] = {
            "email": "client@example.com",
            "plan": "starter",
        }
        self.redis.hashes["apikey:hash_2"] = {
            "email": "second@example.com",
            "plan": "free",
        }
        self.redis.strings["usage:hash_1:2026-03"] = "12"
        self.redis.strings["usage:hash_2:2026-03"] = "8"
        self.redis.sets["pilot_request_emails"] = {"lead@example.com"}
        self.redis.sets["upgrade_request_emails"] = {"client@example.com"}
        self.redis.strings["total_savings_inr"] = "280"
        self.redis.strings["stat:velocity"] = "5"
        self.redis.strings["stat:sybil"] = "2"

        with patch.object(self.module.time, "strftime", return_value="2026-03"):
            response = self.client.get(
                "/v1/admin/business-metrics",
                headers={"X-Admin-Key": self.module.ADMIN_KEY},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["active_merchants"], 2)
        self.assertEqual(payload["paid_merchants"], 1)
        self.assertEqual(payload["monthly_api_calls"], 20)
        self.assertEqual(payload["pilot_requests"], 1)
        self.assertEqual(payload["upgrade_requests"], 1)
        self.assertEqual(payload["risk_signal_counts"]["velocity"], 5)

    def test_auth_me_reads_usage_by_api_key_hash(self):
        raw_key = "vp_live_example"
        key_hash = self.module._hash_key(raw_key)
        self.redis.hashes["user:user@example.com"] = {
            "pwd_hash": "hash",
            "salt": "salt",
            "key_hash": key_hash,
            "key_prefix": raw_key[:8],
            "key_suffix": raw_key[-4:],
            "plan": "free",
        }
        self.redis.strings["session:test-session"] = "user@example.com"
        self.redis.strings[f"usage:{key_hash}:2026-03"] = "7"
        self.client.cookies.set("vp_session", "test-session")

        with patch.object(self.module.time, "strftime", return_value="2026-03"):
            response = self.client.get("/v1/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["metrics"]["usage"], 7)
        self.assertEqual(response.json()["api_key"], f"{raw_key[:8]}...{raw_key[-4:]}")

    def test_auth_reporting_returns_recent_decisions(self):
        raw_key = "vp_live_reporting"
        key_hash = self.module._hash_key(raw_key)
        self.redis.hashes["user:user@example.com"] = {
            "pwd_hash": "hash",
            "salt": "salt",
            "key_hash": key_hash,
            "key_prefix": raw_key[:8],
            "key_suffix": raw_key[-4:],
            "plan": "growth",
        }
        self.redis.strings["session:test-session"] = "user@example.com"
        self.redis.strings[f"usage:{key_hash}:2026-03"] = "23"
        self.redis.strings["savings:user@example.com"] = "140"
        self.client.cookies.set("vp_session", "test-session")

        async def fake_recent(email, limit=12):
            return [
                {
                    "risk_id": "risk-1",
                    "uid": "buyer-1",
                    "risk_score": 68.4,
                    "decision": "FORCE_PREPAID",
                    "reasons": "HIGH_VELOCITY,LOW_TRUST_SCORE",
                    "timestamp": 1710000000.0,
                    "outcome": "PENDING",
                },
                {
                    "risk_id": "risk-2",
                    "uid": "buyer-2",
                    "risk_score": 18.2,
                    "decision": "ALLOW_COD",
                    "reasons": "",
                    "timestamp": 1710000500.0,
                    "outcome": "RTO",
                },
            ]

        with patch.object(self.module.time, "strftime", return_value="2026-03"):
            with patch.object(self.module.AUDIT_STORE, "fetch_recent_risk_audits", fake_recent):
                response = self.client.get("/v1/auth/reporting")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["screened_this_month"], 23)
        self.assertEqual(payload["summary"]["recent_force_prepaid"], 1)
        self.assertEqual(payload["summary"]["recent_allow_cod"], 1)
        self.assertEqual(payload["summary"]["recent_rto"], 1)
        self.assertEqual(payload["top_factors"][0]["label"], "HIGH_VELOCITY")

    def test_auth_settings_can_be_updated(self):
        raw_key = "vp_live_settings"
        key_hash = self.module._hash_key(raw_key)
        self.redis.hashes["user:user@example.com"] = {
            "pwd_hash": "hash",
            "salt": "salt",
            "key_hash": key_hash,
            "plan": "free",
        }
        self.redis.strings["session:test-session"] = "user@example.com"
        self.client.cookies.set("vp_session", "test-session")

        response = self.client.post(
            "/v1/auth/settings",
            json={
                "company_name": "Vector Commerce",
                "category": "Beauty",
                "monthly_orders": "1000-5000",
                "cod_share": "40-60%",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.redis.hashes["user:user@example.com"]["company_name"], "Vector Commerce")
        self.assertEqual(self.redis.hashes["user:user@example.com"]["category"], "Beauty")

    def test_auth_upgrade_request_is_persisted(self):
        raw_key = "vp_live_upgrade"
        key_hash = self.module._hash_key(raw_key)
        self.redis.hashes["user:user@example.com"] = {
            "pwd_hash": "hash",
            "salt": "salt",
            "key_hash": key_hash,
            "plan": "free",
        }
        self.redis.strings["session:test-session"] = "user@example.com"
        self.client.cookies.set("vp_session", "test-session")

        response = self.client.post(
            "/v1/auth/upgrade-request",
            json={"requested_plan": "growth", "note": "Need higher monthly volume."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.redis.hashes["upgrade_request:user@example.com"]["requested_plan"], "growth")
        self.assertIn("user@example.com", self.redis.sets["upgrade_request_emails"])

    def test_auth_can_read_upgrade_request_status(self):
        raw_key = "vp_live_upgrade_status"
        key_hash = self.module._hash_key(raw_key)
        self.redis.hashes["user:user@example.com"] = {
            "pwd_hash": "hash",
            "salt": "salt",
            "key_hash": key_hash,
            "plan": "free",
        }
        self.redis.hashes["upgrade_request:user@example.com"] = {
            "email": "user@example.com",
            "current_plan": "free",
            "requested_plan": "growth",
            "status": "approved",
            "submitted_at": "1710000000.0",
        }
        self.redis.strings["session:test-session"] = "user@example.com"
        self.client.cookies.set("vp_session", "test-session")

        response = self.client.get("/v1/auth/upgrade-request")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["request"]["status"], "approved")
        self.assertEqual(response.json()["request"]["requested_plan"], "growth")

    def test_admin_session_allows_dashboard_without_header(self):
        login_response = self.client.post(
            "/v1/admin/session",
            json={"admin_key": self.module.ADMIN_KEY},
        )
        self.assertEqual(login_response.status_code, 200)

        self.redis.strings["total_savings_inr"] = "0"
        response = self.client.get("/v1/admin/users")
        self.assertEqual(response.status_code, 200)
        self.assertIn("users", response.json())

    def test_risk_check_returns_forced_prepaid_for_high_risk_order(self):
        raw_key = "vp_live_risk"
        key_hash = self.module._hash_key(raw_key)
        self.redis.hashes[f"apikey:{key_hash}"] = {
            "email": "merchant@example.com",
            "plan": "starter",
            "key_prefix": raw_key[:8],
            "key_suffix": raw_key[-4:],
            "created_at": "2026-03-13T00:00:00Z",
        }

        async def fake_velocity(uid, risk_config, merchant_key_hash):
            return True

        async def fake_sybil(uid, address, risk_config, merchant_key_hash, merchant_email):
            return True

        async def fake_price(uid, amount, risk_config, merchant_key_hash):
            return True, 1000.0, 50.0

        async def fake_trust(uid, merchant_key_hash):
            return 10.0

        async def fake_ip(ip):
            return True

        async def fake_log(*args, **kwargs):
            return None

        with (
            patch.object(self.module, "_check_velocity", fake_velocity),
            patch.object(self.module, "_check_sybil", fake_sybil),
            patch.object(self.module, "_check_price_anomaly", fake_price),
            patch.object(self.module, "_get_trust_score", fake_trust),
            patch.object(self.module, "_check_ip_intelligence", fake_ip),
            patch.object(self.module, "_log_audit_event", fake_log),
        ):
            response = self.client.post(
                "/v1/risk-check",
                headers={"X-API-Key": raw_key},
                json={
                    "uid": "user-1",
                    "amt": 2500,
                    "addr": "HSR Layout",
                    "pin": "560102",
                    "ip": "8.8.8.8",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decision"], "FORCE_PREPAID")
        self.assertIn("HIGH_VELOCITY", payload["risk_factors"])
        self.assertIn("ADDRESS_SYBIL_DETECTED", payload["risk_factors"])

    def test_merchant_state_keys_are_namespaced_by_key_hash(self):
        key_hash = "merchant_hash"
        self.assertEqual(
            self.module._merchant_state_key(key_hash, "history", "user-1"),
            "history:merchant_hash:user-1",
        )

    def test_risk_decision_threshold_is_runtime_configurable(self):
        with patch.dict(
            self.module.RISK_CONFIG,
            {
                "velocity_weight": 20.0,
                "sybil_weight": 15.0,
                "anomaly_weight": 10.0,
                "vpn_weight": 5.0,
                "trust_floor": 30.0,
                "trust_penalty_multiplier": 0.5,
                "decision_threshold": 90.0,
            },
            clear=False,
        ):
            score = self.module._calculate_risk_score(
                velocity_flag=True,
                sybil_flag=True,
                anomaly_flag=True,
                identity_flag=False,
                cohort_flag=False,
                trust_score=20.0,
                vpn_flag=False,
                global_network_flag=False,
                gibberish_flag=False,
                device_velocity_flag=False,
                suspicious_name_flag=False,
                geo_velocity_flag=False,
                time_anomaly_flag=False,
                bot_speed_flag=False,
                suspicious_phone_flag=False,
                disposable_email_flag=False,
                email_name_mismatch_flag=False,
                poor_address_flag=False,
                high_risk_pin_flag=False,
                risk_config=self.module.RISK_CONFIG,
            )

        self.assertEqual(score, 50.0)
        self.assertLess(score, 90.0)

    def test_admin_can_explain_risk_event_via_session(self):
        self.redis.strings["explain:risk-1"] = (
            '{"score": 55.0, "flags": ["HIGH_VELOCITY"], '
            '"metrics": {"velocity": true, "sybil": false, "price": false, "trust": 50.0, "vpn": false}, '
            '"timestamp": 1710000000.0}'
        )

        login_response = self.client.post(
            "/v1/admin/session",
            json={"admin_key": self.module.ADMIN_KEY},
        )
        self.assertEqual(login_response.status_code, 200)

        response = self.client.get("/v1/explain/risk-1")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["decision"], "FORCE_PREPAID")
        self.assertTrue(payload["findings"])

    def test_admin_can_update_merchant_risk_profile(self):
        self.redis.sets["admin:all_keys"] = {"hash_profile"}
        self.redis.hashes["apikey:hash_profile"] = {
            "email": "merchant@example.com",
            "plan": "starter",
            "key_prefix": "vp_profi",
            "key_suffix": "file",
        }
        self.redis.strings["emailkey:merchant@example.com"] = "hash_profile"

        response = self.client.post(
            "/v1/admin/risk-config/merchant@example.com",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
            json={
                "decision_threshold": 72,
                "velocity_max_orders": 6,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["risk_profile"]["decision_threshold"], 72.0)
        self.assertEqual(payload["risk_profile"]["velocity_max_orders"], 6)
        self.assertTrue(payload["is_custom"])
        self.assertEqual(
            self.redis.hashes["apikey:hash_profile"]["risk_decision_threshold"],
            "72.0",
        )

    def test_admin_risk_profile_rejects_out_of_range_values(self):
        self.redis.sets["admin:all_keys"] = {"hash_profile"}
        self.redis.hashes["apikey:hash_profile"] = {
            "email": "merchant@example.com",
            "plan": "starter",
            "key_prefix": "vp_profi",
            "key_suffix": "file",
        }
        self.redis.strings["emailkey:merchant@example.com"] = "hash_profile"

        response = self.client.post(
            "/v1/admin/risk-config/merchant@example.com",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
            json={"decision_threshold": 200},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("decision_threshold", response.json()["detail"])

    def test_admin_can_reset_merchant_risk_profile(self):
        self.redis.sets["admin:all_keys"] = {"hash_profile"}
        self.redis.hashes["apikey:hash_profile"] = {
            "email": "merchant@example.com",
            "plan": "starter",
            "key_prefix": "vp_profi",
            "key_suffix": "file",
            "risk_decision_threshold": "72.0",
            "risk_velocity_max_orders": "6",
        }
        self.redis.strings["emailkey:merchant@example.com"] = "hash_profile"

        response = self.client.delete(
            "/v1/admin/risk-config/merchant@example.com",
            headers={"X-Admin-Key": self.module.ADMIN_KEY},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["is_custom"])
        self.assertNotIn("risk_decision_threshold", self.redis.hashes["apikey:hash_profile"])

    def test_admin_can_view_risk_profile_history(self):
        async def fake_history(email, limit=10):
            self.assertEqual(email, "merchant@example.com")
            self.assertEqual(limit, 10)
            return [
                {
                    "audit_id": "audit-1",
                    "email": email,
                    "actor": "admin@example.com",
                    "action": "UPDATE",
                    "previous_config": json.dumps({"decision_threshold": 40.0}),
                    "new_config": json.dumps({"decision_threshold": 72.0}),
                    "timestamp": 1710000000.0,
                }
            ]

        with patch.object(self.module.AUDIT_STORE, "fetch_risk_profile_audits", fake_history):
            response = self.client.get(
                "/v1/admin/risk-config-history/merchant@example.com",
                headers={"X-Admin-Key": self.module.ADMIN_KEY},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["email"], "merchant@example.com")
        self.assertEqual(len(payload["history"]), 1)
        self.assertEqual(payload["history"][0]["actor"], "admin@example.com")
        self.assertEqual(payload["history"][0]["new_config"]["decision_threshold"], 72.0)

    def test_admin_page_sets_no_store_and_security_headers(self):
        response = self.client.get("/admin")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["pragma"], "no-cache")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])

    def test_health_reports_redis_and_audit_backend(self):
        async def fake_healthcheck():
            return True

        with patch.object(self.module.AUDIT_STORE, "healthcheck", fake_healthcheck):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["redis"], "connected")
        self.assertEqual(payload["audit"], "connected")
        self.assertEqual(payload["audit_backend"], self.module.AUDIT_STORE.backend)

    def test_health_degrades_when_audit_backend_is_unreachable(self):
        async def fake_healthcheck():
            return False

        with patch.object(self.module.AUDIT_STORE, "healthcheck", fake_healthcheck):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["audit"], "unreachable")

    def test_readiness_returns_503_when_dependencies_are_unavailable(self):
        async def fake_healthcheck():
            return False

        with patch.object(self.module.AUDIT_STORE, "healthcheck", fake_healthcheck):
            response = self.client.get("/readyz")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["audit"], "unreachable")

    def test_multiple_admin_emails_are_supported(self):
        self.assertTrue(self.module._is_admin_email(self.module.PRIMARY_ADMIN_EMAIL))
        self.assertFalse(self.module._is_admin_email("user@example.com"))

    def test_production_runtime_config_requires_postgres_and_secure_cookie(self):
        with (
            patch.object(self.module, "ENVIRONMENT", "production"),
            patch.object(self.module, "DATABASE_URL", ""),
            patch.object(self.module, "SESSION_COOKIE_SECURE", False),
            patch.object(self.module, "ADMIN_KEY", "vp_admin_changeme"),
            patch.dict(os.environ, {}, clear=False),
        ):
            with self.assertRaises(RuntimeError):
                self.module._validate_runtime_config()

    def test_outcome_rejects_unknown_status(self):
        raw_key = "vp_live_outcome"
        key_hash = self.module._hash_key(raw_key)
        self.redis.hashes[f"apikey:{key_hash}"] = {
            "email": "merchant@example.com",
            "plan": "starter",
            "key_prefix": raw_key[:8],
            "key_suffix": raw_key[-4:],
            "created_at": "2026-03-13T00:00:00Z",
        }

        response = self.client.post(
            "/v1/outcome",
            headers={"X-API-Key": raw_key},
            json={"risk_id": "risk-1", "status": "UNKNOWN"},
        )

        self.assertEqual(response.status_code, 422)

    def test_delete_user_removes_user_and_api_key_records(self):
        raw_key = "vp_live_delete"
        key_hash = self.module._hash_key(raw_key)
        self.redis.hashes["user:delete@example.com"] = {
            "key_hash": key_hash,
            "key_prefix": raw_key[:8],
            "key_suffix": raw_key[-4:],
            "plan": "free",
        }
        self.redis.hashes[f"apikey:{key_hash}"] = {
            "email": "delete@example.com",
            "plan": "free",
            "key_prefix": raw_key[:8],
            "key_suffix": raw_key[-4:],
        }
        self.redis.sets["admin:all_keys"] = {key_hash}
        self.redis.strings["emailkey:delete@example.com"] = key_hash
        self.redis.strings[f"usage:{key_hash}:2026-03"] = "4"
        self.redis.sets[f"usage_index:{key_hash}"] = {f"usage:{key_hash}:2026-03"}

        with patch.object(self.module.time, "strftime", return_value="2026-03"):
            response = self.client.delete(
                "/v1/admin/user/delete@example.com",
                headers={"X-Admin-Key": self.module.ADMIN_KEY},
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("user:delete@example.com", self.redis.hashes)
        self.assertNotIn(f"apikey:{key_hash}", self.redis.hashes)
        self.assertEqual(self.redis.sets["admin:all_keys"], set())


if __name__ == "__main__":
    unittest.main()
