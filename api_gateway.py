from contextlib import asynccontextmanager
from uuid import uuid4
import asyncio
from urllib import request as urllib_request
from urllib.error import URLError

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Header, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import vector_pulse
import os
import time
import logging
import secrets
import hashlib
import aiosqlite
import json
from geolite2 import geolite2
from typing import Any, Literal

try:
    import asyncpg
except ImportError:
    asyncpg = None

# ── Logging setup ──────────────────────────────────────────────────────────────
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def _log_event(event: str, **fields):
    payload = {"event": event, **fields}
    logging.info(json.dumps(payload, default=str, sort_keys=True))

def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


# ── Database Initialization ────────────────────────────────────────────────────
AUDIT_DB = "audit_log.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
PILOT_REQUEST_WEBHOOK_URL = os.getenv("PILOT_REQUEST_WEBHOOK_URL", "").strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


async def _send_pilot_request_webhook(payload: dict[str, Any]) -> None:
    if not PILOT_REQUEST_WEBHOOK_URL:
        return

    body = json.dumps(
        {
            "event": "pilot_request_created",
            "lead": payload,
        }
    ).encode("utf-8")

    def _post_webhook() -> None:
        req = urllib_request.Request(
            PILOT_REQUEST_WEBHOOK_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=3) as response:
            response.read()

    try:
        await asyncio.to_thread(_post_webhook)
        _log_event("pilot_request_webhook_sent", email=payload.get("email"))
    except (URLError, TimeoutError, OSError) as exc:
        logging.warning(f"Pilot request webhook failed: {exc}")


class AuditStore:
    def __init__(self, database_url: str, sqlite_path: str):
        self.database_url = database_url
        self.sqlite_path = sqlite_path
        self.pool = None
        self.backend = "postgres" if database_url else "sqlite"

    async def init(self):
        if self.backend == "postgres":
            if asyncpg is None:
                raise RuntimeError("DATABASE_URL is set but asyncpg is not installed")
            self.pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS risk_audit (
                        risk_id TEXT PRIMARY KEY,
                        uid TEXT,
                        email TEXT,
                        risk_score DOUBLE PRECISION,
                        decision TEXT,
                        shadow_mode INTEGER,
                        reasons TEXT,
                        metrics TEXT,
                        timestamp DOUBLE PRECISION,
                        outcome TEXT DEFAULT 'PENDING'
                    )
                """)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS risk_profile_audit (
                        audit_id TEXT PRIMARY KEY,
                        email TEXT,
                        actor TEXT,
                        action TEXT,
                        previous_config TEXT,
                        new_config TEXT,
                        timestamp DOUBLE PRECISION
                    )
                """)
            return

        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS risk_audit (
                    risk_id TEXT PRIMARY KEY,
                    uid TEXT,
                    email TEXT,
                    risk_score REAL,
                    decision TEXT,
                    shadow_mode INTEGER,
                    reasons TEXT,
                    metrics TEXT,
                    timestamp REAL,
                    outcome TEXT DEFAULT 'PENDING'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS risk_profile_audit (
                    audit_id TEXT PRIMARY KEY,
                    email TEXT,
                    actor TEXT,
                    action TEXT,
                    previous_config TEXT,
                    new_config TEXT,
                    timestamp REAL
                )
            """)
            await db.commit()

    async def close(self):
        if self.pool is not None:
            await self.pool.close()

    async def insert_risk_audit(self, payload: dict[str, Any]):
        if self.backend == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO risk_audit
                    (risk_id, uid, email, risk_score, decision, shadow_mode, reasons, metrics, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    payload["risk_id"],
                    payload["uid"],
                    payload["email"],
                    payload["risk_score"],
                    payload["decision"],
                    payload["shadow_mode"],
                    payload["reasons"],
                    payload["metrics"],
                    payload["timestamp"],
                )
            return

        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute(
                """
                INSERT INTO risk_audit
                (risk_id, uid, email, risk_score, decision, shadow_mode, reasons, metrics, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["risk_id"],
                    payload["uid"],
                    payload["email"],
                    payload["risk_score"],
                    payload["decision"],
                    payload["shadow_mode"],
                    payload["reasons"],
                    payload["metrics"],
                    payload["timestamp"],
                ),
            )
            await db.commit()

    async def insert_risk_profile_audit(self, payload: dict[str, Any]):
        if self.backend == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO risk_profile_audit
                    (audit_id, email, actor, action, previous_config, new_config, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    payload["audit_id"],
                    payload["email"],
                    payload["actor"],
                    payload["action"],
                    payload["previous_config"],
                    payload["new_config"],
                    payload["timestamp"],
                )
            return

        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute(
                """
                INSERT INTO risk_profile_audit
                (audit_id, email, actor, action, previous_config, new_config, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["audit_id"],
                    payload["email"],
                    payload["actor"],
                    payload["action"],
                    payload["previous_config"],
                    payload["new_config"],
                    payload["timestamp"],
                ),
            )
            await db.commit()

    async def delete_user_audits(self, email: str):
        if self.backend == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM risk_audit WHERE email = $1", email)
                await conn.execute("DELETE FROM risk_profile_audit WHERE email = $1", email)
            return

        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute("DELETE FROM risk_audit WHERE email = ?", (email,))
            await db.execute("DELETE FROM risk_profile_audit WHERE email = ?", (email,))
            await db.commit()

    async def fetch_risk_audit(self, risk_id: str):
        if self.backend == "postgres":
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM risk_audit WHERE risk_id = $1", risk_id)
                return dict(row) if row else None

        async with aiosqlite.connect(self.sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM risk_audit WHERE risk_id = ?", (risk_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_outcome(self, risk_id: str, status: str):
        if self.backend == "postgres":
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE risk_audit SET outcome = $1 WHERE risk_id = $2",
                    status,
                    risk_id,
                )
            return

        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute(
                "UPDATE risk_audit SET outcome = ? WHERE risk_id = ?",
                (status, risk_id),
            )
            await db.commit()

    async def fetch_risk_profile_audits(self, email: str, limit: int = 10):
        if self.backend == "postgres":
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT audit_id, email, actor, action, previous_config, new_config, timestamp
                    FROM risk_profile_audit
                    WHERE email = $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """,
                    email,
                    limit,
                )
                return [dict(row) for row in rows]

        async with aiosqlite.connect(self.sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT audit_id, email, actor, action, previous_config, new_config, timestamp
                FROM risk_profile_audit
                WHERE email = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (email, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def fetch_recent_risk_audits(self, email: str, limit: int = 12):
        if self.backend == "postgres":
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome
                    FROM risk_audit
                    WHERE email = $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                    """,
                    email,
                    limit,
                )
                return [dict(row) for row in rows]

        async with aiosqlite.connect(self.sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome
                FROM risk_audit
                WHERE email = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (email, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def healthcheck(self) -> bool:
        try:
            if self.backend == "postgres":
                async with self.pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                return True

            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("SELECT 1")
            return True
        except Exception:
            return False


AUDIT_STORE = AuditStore(DATABASE_URL, AUDIT_DB)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _validate_runtime_config()
    await AUDIT_STORE.init()
    _log_event(
        "startup_complete",
        environment=ENVIRONMENT,
        audit_backend=AUDIT_STORE.backend,
        admin_count=len(ADMIN_EMAILS),
    )
    try:
        yield
    finally:
        await AUDIT_STORE.close()
        _log_event("shutdown_complete", environment=ENVIRONMENT)


app = FastAPI(
    title="Vector-Pulse RTO Shield API",
    description="Real-time fraud detection for Indian e-commerce. Stop RTO losses instantly.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Admin-Key"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self' data:; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    _log_event(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
        client=getattr(request.client, "host", None),
    )
    return response

# ── IP Intelligence Initialization ─────────────────────────────────────────────
GEO_READER = geolite2.reader()

# ── Redis Feature Store ────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

import redis.asyncio as redis

# ── Redis Feature Store (Async) ────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
    ssl=REDIS_SSL,
    retry_on_timeout=True,
    health_check_interval=30
)

RATE_LIMITS = {
    "free": 1_000,
    "starter": 10_000,
    "growth": 100_000,
    "scale": 1_000_000,
}

RISK_CONFIG = {
    "history_len": _env_int("RISK_HISTORY_LEN", 10),
    "z_score_threshold": _env_float("RISK_Z_SCORE_THRESHOLD", 3.0),
    "velocity_window_secs": _env_int("RISK_VELOCITY_WINDOW_SECS", 5),
    "velocity_max_orders": _env_int("RISK_VELOCITY_MAX_ORDERS", 3),
    "sybil_address_limit": _env_int("RISK_SYBIL_ADDRESS_LIMIT", 3),
    "decision_threshold": _env_float("RISK_DECISION_THRESHOLD", 40.0),
    "velocity_weight": _env_float("RISK_WEIGHT_VELOCITY", 35.0),
    "sybil_weight": _env_float("RISK_WEIGHT_SYBIL", 25.0),
    "anomaly_weight": _env_float("RISK_WEIGHT_ANOMALY", 20.0),
    "identity_weight": _env_float("RISK_WEIGHT_IDENTITY", 18.0),
    "cohort_weight": _env_float("RISK_WEIGHT_COHORT", 12.0),
    "vpn_weight": _env_float("RISK_WEIGHT_VPN", 15.0),
    "trust_floor": _env_float("RISK_TRUST_FLOOR", 30.0),
    "trust_penalty_multiplier": _env_float("RISK_TRUST_PENALTY_MULTIPLIER", 0.5),
    "burst_fraction_per_minute": _env_float("RATE_LIMIT_BURST_FRACTION", 0.001),
    "savings_per_block_inr": _env_int("RISK_SAVINGS_PER_BLOCK_INR", 70),
    "review_threshold": _env_float("RISK_REVIEW_THRESHOLD", 28.0),
    "global_network_weight": _env_float("RISK_WEIGHT_GLOBAL", 45.0),
    "gibberish_weight": _env_float("RISK_WEIGHT_GIBBERISH", 30.0),
    "device_velocity_weight": _env_float("RISK_WEIGHT_DEVICE_VELOCITY", 40.0),
    "suspicious_name_weight": _env_float("RISK_WEIGHT_SUSPICIOUS_NAME", 20.0),
    "geo_velocity_weight": _env_float("RISK_WEIGHT_GEO_VELOCITY", 40.0),
    "time_anomaly_weight": _env_float("RISK_WEIGHT_TIME_ANOMALY", 10.0),
    "bot_speed_weight": _env_float("RISK_WEIGHT_BOT_SPEED", 50.0),
    "suspicious_phone_weight": _env_float("RISK_WEIGHT_SUSPICIOUS_PHONE", 30.0),
    "disposable_email_weight": _env_float("RISK_WEIGHT_DISPOSABLE_EMAIL", 45.0),
    "email_name_mismatch_weight": _env_float("RISK_WEIGHT_EMAIL_NAME_MISMATCH", 25.0),
    "poor_address_weight": _env_float("RISK_WEIGHT_POOR_ADDRESS", 15.0),
    "high_risk_pin_weight": _env_float("RISK_WEIGHT_HIGH_RISK_PIN", 35.0),
}
RISK_CONFIG_TYPES = {
    "history_len": int,
    "z_score_threshold": float,
    "velocity_window_secs": int,
    "velocity_max_orders": int,
    "sybil_address_limit": int,
    "decision_threshold": float,
    "velocity_weight": float,
    "sybil_weight": float,
    "anomaly_weight": float,
    "identity_weight": float,
    "cohort_weight": float,
    "vpn_weight": float,
    "trust_floor": float,
    "trust_penalty_multiplier": float,
    "burst_fraction_per_minute": float,
    "savings_per_block_inr": int,
    "review_threshold": float,
    "global_network_weight": float,
    "gibberish_weight": float,
    "device_velocity_weight": float,
    "suspicious_name_weight": float,
    "geo_velocity_weight": float,
    "time_anomaly_weight": float,
    "bot_speed_weight": float,
    "suspicious_phone_weight": float,
    "disposable_email_weight": float,
    "email_name_mismatch_weight": float,
    "poor_address_weight": float,
    "high_risk_pin_weight": float,
}
RISK_CONFIG_BOUNDS = {
    "history_len": (1, 500),
    "z_score_threshold": (0.1, 10.0),
    "velocity_window_secs": (1, 3600),
    "velocity_max_orders": (1, 1000),
    "sybil_address_limit": (1, 1000),
    "decision_threshold": (0.0, 100.0),
    "velocity_weight": (0.0, 100.0),
    "sybil_weight": (0.0, 100.0),
    "anomaly_weight": (0.0, 100.0),
    "identity_weight": (0.0, 100.0),
    "cohort_weight": (0.0, 100.0),
    "vpn_weight": (0.0, 100.0),
    "trust_floor": (0.0, 100.0),
    "trust_penalty_multiplier": (0.0, 10.0),
    "burst_fraction_per_minute": (0.000001, 1.0),
    "savings_per_block_inr": (1, 1000000),
    "review_threshold": (0.0, 100.0),
    "global_network_weight": (0.0, 100.0),
    "gibberish_weight": (0.0, 100.0),
    "device_velocity_weight": (0.0, 100.0),
    "suspicious_name_weight": (0.0, 100.0),
    "geo_velocity_weight": (0.0, 100.0),
    "time_anomaly_weight": (0.0, 100.0),
    "bot_speed_weight": (0.0, 100.0),
    "suspicious_phone_weight": (0.0, 100.0),
    "disposable_email_weight": (0.0, 100.0),
    "email_name_mismatch_weight": (0.0, 100.0),
    "poor_address_weight": (0.0, 100.0),
    "high_risk_pin_weight": (0.0, 100.0),
}

# ── API Key Auth ───────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "vp_admin_changeme")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "cherukurigowtham851@gmail.com")
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", ADMIN_EMAIL).split(",")
    if email.strip()
}
PRIMARY_ADMIN_EMAIL = next(iter(ADMIN_EMAILS)) if ADMIN_EMAILS else ADMIN_EMAIL.lower()
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", ENVIRONMENT == "production")


def _is_admin_email(email: str | None) -> bool:
    return bool(email and email.lower() in ADMIN_EMAILS)


def _validate_runtime_config() -> None:
    if ENVIRONMENT != "production":
        return

    errors = []
    cors_origins = _parse_cors_origins()

    if ADMIN_KEY == "vp_admin_changeme":
        errors.append("ADMIN_SECRET_KEY must be set in production")
    if not DATABASE_URL:
        errors.append("DATABASE_URL must be set in production")
    if not os.getenv("CORS_ALLOW_ORIGINS"):
        errors.append("CORS_ALLOW_ORIGINS must be set in production")
    if any("localhost" in origin or "127.0.0.1" in origin for origin in cors_origins):
        errors.append("CORS_ALLOW_ORIGINS must not contain localhost origins in production")
    if not SESSION_COOKIE_SECURE:
        errors.append("SESSION_COOKIE_SECURE must be enabled in production")
    if not ADMIN_EMAILS:
        errors.append("ADMIN_EMAILS or ADMIN_EMAIL must define at least one admin email")

    if errors:
        raise RuntimeError("; ".join(errors))


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _key_preview(prefix: str | None, suffix: str | None) -> str:
    if not prefix or not suffix:
        return "REDACTED"
    return f"{prefix}...{suffix}"


def _key_metadata(raw_key: str) -> dict:
    return {
        "key_hash": _hash_key(raw_key),
        "key_prefix": raw_key[:8],
        "key_suffix": raw_key[-4:],
    }


def _coerce_risk_value(name: str, value):
    caster = RISK_CONFIG_TYPES[name]
    return caster(value)


def _resolve_risk_config(source: dict | None) -> dict:
    config = dict(RISK_CONFIG)
    if not source:
        return config

    for name in RISK_CONFIG:
        raw_value = source.get(f"risk_{name}")
        if raw_value is None:
            continue
        config[name] = _coerce_risk_value(name, raw_value)

    return config


def _has_custom_risk_profile(source: dict | None) -> bool:
    if not source:
        return False
    return any(source.get(f"risk_{name}") is not None for name in RISK_CONFIG)


def _validate_risk_value(name: str, value):
    low, high = RISK_CONFIG_BOUNDS[name]
    if value < low or value > high:
        raise HTTPException(
            status_code=400,
            detail=f"{name} must be between {low} and {high}",
        )
    return value


def _calculate_risk_score(
    velocity_flag: bool,
    sybil_flag: bool,
    anomaly_flag: bool,
    identity_flag: bool,
    cohort_flag: bool,
    trust_score: float,
    vpn_flag: bool,
    global_network_flag: bool,
    gibberish_flag: bool,
    device_velocity_flag: bool,
    suspicious_name_flag: bool,
    geo_velocity_flag: bool,
    time_anomaly_flag: bool,
    bot_speed_flag: bool,
    suspicious_phone_flag: bool,
    disposable_email_flag: bool,
    email_name_mismatch_flag: bool,
    poor_address_flag: bool,
    high_risk_pin_flag: bool,
    risk_config: dict,
) -> float:
    score = 0.0

    if velocity_flag:
        score += risk_config["velocity_weight"]
    if sybil_flag:
        score += risk_config["sybil_weight"]
    if anomaly_flag:
        score += risk_config["anomaly_weight"]
    if identity_flag:
        score += risk_config["identity_weight"]
    if cohort_flag:
        score += risk_config["cohort_weight"]
    if vpn_flag:
        score += risk_config["vpn_weight"]
    if global_network_flag:
        score += risk_config["global_network_weight"]
    if gibberish_flag:
        score += risk_config["gibberish_weight"]
    if device_velocity_flag:
        score += risk_config["device_velocity_weight"]
    if suspicious_name_flag:
        score += risk_config["suspicious_name_weight"]
    if geo_velocity_flag:
        score += risk_config["geo_velocity_weight"]
    if time_anomaly_flag:
        score += risk_config["time_anomaly_weight"]
    if bot_speed_flag:
        score += risk_config["bot_speed_weight"]
    if suspicious_phone_flag:
        score += risk_config["suspicious_phone_weight"]
    if disposable_email_flag:
        score += risk_config["disposable_email_weight"]
    if email_name_mismatch_flag:
        score += risk_config["email_name_mismatch_weight"]
    if poor_address_flag:
        score += risk_config["poor_address_weight"]
    if high_risk_pin_flag:
        score += risk_config["high_risk_pin_weight"]

    trust_floor = risk_config["trust_floor"]
    if trust_score < trust_floor:
        score += (trust_floor - trust_score) * risk_config["trust_penalty_multiplier"]

    return max(0.0, min(100.0, score))


async def _find_key_hash_by_email(email: str) -> str | None:
    key_hash = await r.get(f"emailkey:{email}")
    if key_hash:
        return key_hash

    legacy_hashes = await r.smembers("admin:all_keys")
    for candidate in legacy_hashes:
        profile = await r.hgetall(f"apikey:{candidate}")
        if profile.get("email") == email:
            await r.set(f"emailkey:{email}", candidate)
            return candidate
    return None


async def _create_session(email: str, response: Response, request: Request) -> None:
    session_id = secrets.token_urlsafe(64)
    await r.setex(f"session:{session_id}", 86400 * 30, email)
    await r.sadd(f"session_index:{email}", session_id)

    response.set_cookie(
        key="vp_session",
        value=session_id,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=86400 * 30,
    )


async def _clear_user_sessions(email: str) -> None:
    session_ids = await r.smembers(f"session_index:{email}")
    if not session_ids:
        await r.delete(f"session_index:{email}")
        return

    async with r.pipeline() as pipe:
        for session_id in session_ids:
            pipe.delete(f"session:{session_id}")
        pipe.delete(f"session_index:{email}")
        await pipe.execute()


def _merchant_scope(key_hash: str | None) -> str:
    return key_hash or "anonymous"


def _merchant_state_key(key_hash: str | None, kind: str, suffix: str) -> str:
    return f"{kind}:{_merchant_scope(key_hash)}:{suffix}"


def _ip_prefix(ip: str) -> str:
    if ":" in ip:
        return ":".join(ip.split(":")[:4])
    parts = ip.split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3])
    return ip


async def sliding_window_rate_limit(key_hash: str, limit: int, risk_config: dict) -> bool:
    """
    Implements a 1-minute sliding window rate limiter.
    """
    now = time.time()
    window_start = now - 60
    limit_key = f"rl:window:{key_hash}"
    
    try:
        async with r.pipeline() as pipe:
            pipe.zadd(limit_key, {str(now): now})
            pipe.zremrangebyscore(limit_key, 0, window_start)
            pipe.zcard(limit_key)
            pipe.expire(limit_key, 120)
            res = await pipe.execute()
        
        current_usage = res[2]
        burst_limit = max(1, int(limit * risk_config["burst_fraction_per_minute"]))
        return current_usage <= burst_limit
    except Exception as e:
        logging.error(f"Rate Limiter Failed: {e}")
        return True # Default open on failure

async def require_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    try:
        key_hash = _hash_key(api_key)
        key_data = await r.hgetall(f"apikey:{key_hash}")

        if not key_data:
            raise HTTPException(status_code=403, detail="Invalid API key")

        risk_config = _resolve_risk_config(key_data)

        # 1. Monthly Usage Tracking
        month_key = f"usage:{key_hash}:{time.strftime('%Y-%m')}"
        usage_val = await r.get(month_key)
        usage = int(usage_val or 0)
        plan = key_data.get("plan", "starter")
        limit = RATE_LIMITS.get(plan, RATE_LIMITS["starter"])

        if usage >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Monthly limit of {limit:,} calls reached for {plan} plan.",
            )

        # 2. Sliding Window Burst Protection
        if not await sliding_window_rate_limit(key_hash, limit, risk_config):
             raise HTTPException(status_code=429, detail="Too many requests in a short period (Burst Limit Reached)")

        async with r.pipeline() as pipe:
            pipe.incr(month_key)
            pipe.expire(month_key, 60 * 60 * 24 * 35)
            pipe.sadd(f"usage_index:{key_hash}", month_key)
            await pipe.execute()
            
        key_data["key_hash"] = key_hash
        key_data["api_key_preview"] = _key_preview(
            key_data.get("key_prefix"),
            key_data.get("key_suffix"),
        )
        return key_data
    except Exception as e:
        if isinstance(e, HTTPException): raise
        logging.error(f"Redis Auth Error: {e}")
        raise HTTPException(status_code=500, detail="Identity service temporarily unavailable")


async def require_api_key_or_admin(
    request: Request,
    api_key: str = Security(api_key_header),
    x_admin_key: str = Header(None),
):
    if api_key:
        return await require_api_key(api_key)
    return await require_admin(request, x_admin_key)


# ── Request Models ─────────────────────────────────────────────────────────────
class Order(BaseModel):
    uid: str
    amt: float
    addr: str
    pin: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    ip: str = "127.0.0.1"
    device_hash: str | None = None
    checkout_time_secs: float | None = None
    shadow: bool = False # If True, will NOT block even if risky


class RegisterRequest(BaseModel):
    email: str
    plan: str = "starter"
    admin_key: str


class AdminSessionRequest(BaseModel):
    admin_key: str


class RiskConfigUpdateRequest(BaseModel):
    history_len: int | None = None
    z_score_threshold: float | None = None
    velocity_window_secs: int | None = None
    velocity_max_orders: int | None = None
    sybil_address_limit: int | None = None
    decision_threshold: float | None = None
    velocity_weight: float | None = None
    sybil_weight: float | None = None
    anomaly_weight: float | None = None
    identity_weight: float | None = None
    cohort_weight: float | None = None
    vpn_weight: float | None = None
    trust_floor: float | None = None
    trust_penalty_multiplier: float | None = None
    burst_fraction_per_minute: float | None = None
    savings_per_block_inr: int | None = None
    review_threshold: float | None = None
    global_network_weight: float | None = None
    gibberish_weight: float | None = None
    device_velocity_weight: float | None = None
    suspicious_name_weight: float | None = None
    geo_velocity_weight: float | None = None
    time_anomaly_weight: float | None = None
    bot_speed_weight: float | None = None
    suspicious_phone_weight: float | None = None
    disposable_email_weight: float | None = None


class PublicRegisterRequest(BaseModel):
    email: str


class PilotRequest(BaseModel):
    name: str
    email: str
    company: str
    category: str
    monthly_orders: str
    cod_share: str


class PilotRequestStatusUpdate(BaseModel):
    status: Literal["new", "contacted", "pilot_started", "won", "closed"]


class PilotRequestDetailUpdate(BaseModel):
    assigned_to: str | None = None
    notes: str | None = None


class AuthRequest(BaseModel):
    email: str
    password: str


class MerchantSettingsUpdate(BaseModel):
    company_name: str | None = None
    category: str | None = None
    monthly_orders: str | None = None
    cod_share: str | None = None


class UpgradeRequest(BaseModel):
    requested_plan: Literal["growth", "managed"]
    note: str | None = None


class UpgradeRequestDecision(BaseModel):
    status: Literal["approved", "rejected"]


# ── Fraud Detection Helpers ────────────────────────────────────────────────────
# ── Internal Risk Modules (Optimised) ───────────────────────────────────────────
async def _check_global_velocity(ip: str, risk_config: dict) -> bool:
    try:
        now = time.time()
        window_start = now - risk_config["velocity_window_secs"]
        vel_key = f"global:velocity:ip:{ip}"
        async with r.pipeline() as pipe:
            pipe.zadd(vel_key, {str(now): now})
            pipe.zremrangebyscore(vel_key, 0, window_start)
            pipe.zcard(vel_key)
            pipe.expire(vel_key, risk_config["velocity_window_secs"] * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"] * 2
    except Exception as e:
        logging.error(f"Global Velocity Check Failed: {e}")
        return False

async def _check_geo_velocity(uid: str, ip: str, device_hash: str | None, risk_config: dict) -> bool:
    if not device_hash or not ip:
        return False
        
    try:
        from math import radians, sin, cos, sqrt, atan2
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371.0 # km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            return R * c

        geo_data = georeader.get(ip)
        if not geo_data or not geo_data.get("location"):
            return False
            
        current_lat = geo_data["location"].get("latitude")
        current_lon = geo_data["location"].get("longitude")
        
        if current_lat is None or current_lon is None:
            return False

        now = time.time()
        key = f"geo:velocity:{device_hash}"
        
        last_req = await r.hgetall(key)
        
        async with r.pipeline() as pipe:
            pipe.hset(key, mapping={"lat": str(current_lat), "lon": str(current_lon), "ts": str(now)})
            pipe.expire(key, 86400) # Keep for 24h
            await pipe.execute()

        if not last_req:
            return False
            
        last_lat = float(last_req.get("lat"))
        last_lon = float(last_req.get("lon"))
        last_ts = float(last_req.get("ts"))
        
        time_diff_hours = (now - last_ts) / 3600.0
        if time_diff_hours <= 0.001: # Avoid division by zero
            return False
            
        distance_km = haversine(last_lat, last_lon, current_lat, current_lon)
        speed_kmh = distance_km / time_diff_hours
        
        # Impossible travel threshold e.g. > 1000 km/h (Commercial flights top out around 900)
        return speed_kmh > 1000.0
            
    except Exception as e:
        logging.error(f"Geo Velocity Check Failed: {e}")
        return False


def _check_time_anomaly() -> bool:
    import datetime
    try:
        # Use simple UTC to IST offset for speed (+5:30)
        now_utc = datetime.datetime.utcnow()
        now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
        
        # Flag if between 2:00 AM and 5:00 AM IST
        return 2 <= now_ist.hour < 5
    except Exception as e:
        logging.error(f"Time Anomaly Check Failed: {e}")
        return False
        
def _check_bot_speed(checkout_time_secs: float | None) -> bool:
    if checkout_time_secs is None:
        return False
    # If a user completes checkout in less than 2.5 seconds, it's highly likely a script.
    return checkout_time_secs < 2.5

def _check_disposable_email(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
        
    domain = email.split("@")[1].lower()
    
    disposable_domains = {
        "mailinator.com",
        "yopmail.com",
        "10minutemail.com",
        "guerrillamail.com",
        "temp-mail.org",
        "throwawaymail.com",
        "getnada.com",
        "dropmail.me",
        "fakemail.net",
    }
    
    return domain in disposable_domains

async def _check_high_risk_pin(pin: str) -> bool:
    if not pin:
        return False
    try:
        return await r.sismember("high_risk_pins", pin.strip())
    except Exception as e:
        logging.error(f"High-Risk PIN Check Failed: {e}")
        return False


async def _check_global_sybil(uid: str, address: str, risk_config: dict) -> bool:
    try:
        address_hash = hashlib.sha256(vector_pulse.address_fingerprint(address).encode()).hexdigest()
        key = f"global:sybil:addr:{address_hash}"
        async with r.pipeline() as pipe:
            pipe.sadd(key, uid)
            pipe.scard(key)
            pipe.expire(key, 86400 * 7)
            res = await pipe.execute()
        return res[1] > risk_config["sybil_address_limit"] * 2
    except Exception as e:
        logging.error(f"Global Sybil Check Failed: {e}")
        return False

async def _check_device_velocity(uid: str, device_hash: str | None, risk_config: dict) -> bool:
    if not device_hash:
        return False
    try:
        now = time.time()
        window_start = now - risk_config["velocity_window_secs"]
        vel_key = f"device:velocity:{device_hash}"
        async with r.pipeline() as pipe:
            pipe.zadd(vel_key, {str(now): now})
            pipe.zremrangebyscore(vel_key, 0, window_start)
            pipe.zcard(vel_key)
            pipe.expire(vel_key, risk_config["velocity_window_secs"] * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"]
    except Exception as e:
        logging.error(f"Device Velocity Check Failed: {e}")
        return False

async def _check_velocity(uid: str, risk_config: dict, merchant_key_hash: str | None) -> bool:
    try:
        now = time.time()
        window_start = now - risk_config["velocity_window_secs"]
        vel_key = _merchant_state_key(merchant_key_hash, "velocity", uid)
        async with r.pipeline() as pipe:
            pipe.zadd(vel_key, {str(now): now})
            pipe.zremrangebyscore(vel_key, 0, window_start)
            pipe.zcard(vel_key)
            pipe.expire(vel_key, risk_config["velocity_window_secs"] * 2)
            res = await pipe.execute()
        return res[2] > risk_config["velocity_max_orders"]
    except Exception as e:
        logging.error(f"Velocity Check Failed: {e}")
        return False # Safe fallback

async def _check_sybil(uid: str, address: str, risk_config: dict, merchant_key_hash: str | None, merchant_email: str | None) -> bool:
    try:
        # Use a stable Rust-side fingerprint so near-equivalent addresses collapse together.
        address_hash = hashlib.sha256(vector_pulse.address_fingerprint(address).encode()).hexdigest()
        key = _merchant_state_key(merchant_key_hash, "addr", address_hash)
        async with r.pipeline() as pipe:
            pipe.sadd(key, uid)
            pipe.scard(key)
            pipe.expire(key, 86400 * 7) # Keep for 7 days
            if merchant_email:
                pipe.sadd(f"addr_index:{merchant_email}", key)
            res = await pipe.execute()
        return res[1] > risk_config["sybil_address_limit"]
    except Exception as e:
        logging.error(f"Sybil Check Failed: {e}")
        return False


async def _check_identity_cluster(
    uid: str,
    address: str,
    pin: str,
    ip: str,
    merchant_key_hash: str | None,
    merchant_email: str | None,
) -> tuple[bool, float, dict]:
    try:
        address_fingerprint = vector_pulse.address_fingerprint(address)
        address_hash = hashlib.sha256(address_fingerprint.encode()).hexdigest()
        pin_key = _merchant_state_key(merchant_key_hash, "pin", pin or "unknown")
        subnet = _ip_prefix(ip or "127.0.0.1")
        subnet_key = _merchant_state_key(merchant_key_hash, "subnet", subnet)
        addr_key = _merchant_state_key(merchant_key_hash, "addr", address_hash)

        async with r.pipeline() as pipe:
            pipe.sadd(addr_key, uid)
            pipe.scard(addr_key)
            pipe.expire(addr_key, 86400 * 14)
            pipe.sadd(pin_key, uid)
            pipe.scard(pin_key)
            pipe.expire(pin_key, 86400 * 14)
            pipe.sadd(subnet_key, uid)
            pipe.scard(subnet_key)
            pipe.expire(subnet_key, 86400 * 7)
            if merchant_email:
                pipe.sadd(f"addr_index:{merchant_email}", addr_key)
                pipe.sadd(f"pin_index:{merchant_email}", pin_key)
                pipe.sadd(f"subnet_index:{merchant_email}", subnet_key)
            res = await pipe.execute()

        shared_address_count = int(res[1] or 0)
        shared_pin_count = int(res[4] or 0)
        shared_subnet_count = int(res[7] or 0)
        flagged, score = vector_pulse.evaluate_identity_cluster(
            shared_address_count,
            shared_pin_count,
            shared_subnet_count,
        )
        return flagged, score, {
            "shared_address_count": shared_address_count,
            "shared_pin_count": shared_pin_count,
            "shared_subnet_count": shared_subnet_count,
            "address_fingerprint": address_fingerprint,
            "subnet": subnet,
        }
    except Exception as e:
        logging.error(f"Identity Cluster Check Failed: {e}")
        return False, 0.0, {
            "shared_address_count": 0,
            "shared_pin_count": 0,
            "shared_subnet_count": 0,
            "address_fingerprint": "",
            "subnet": _ip_prefix(ip or "127.0.0.1"),
        }

async def _check_price_anomaly(uid: str, amount: float, risk_config: dict, merchant_key_hash: str | None) -> tuple[bool, float, float]:
    try:
        history_key = _merchant_state_key(merchant_key_hash, "history", uid)
        history_raw = await r.lrange(history_key, 0, risk_config["history_len"] - 1)
        history = [float(x) for x in history_raw]

        is_anomaly, avg, std_dev = vector_pulse.detect_amount_anomaly(
            history,
            amount,
            risk_config["z_score_threshold"],
        )
        
        async with r.pipeline() as pipe:
            pipe.lpush(history_key, amount)
            pipe.ltrim(history_key, 0, risk_config["history_len"] - 1)
            pipe.expire(history_key, 60 * 60 * 24 * 7) # Week TTL
            await pipe.execute()
            
        return is_anomaly, avg, std_dev
    except Exception as e:
        logging.error(f"Price Anomaly Check Failed: {e}")
        return False, 0.0, 0.0


async def _check_cohort_anomaly(
    amount: float,
    pin: str,
    risk_config: dict,
    merchant_key_hash: str | None,
) -> tuple[bool, dict]:
    try:
        merchant_history_key = _merchant_state_key(merchant_key_hash, "merchant_amounts", "all")
        pin_history_key = _merchant_state_key(merchant_key_hash, "pin_amounts", pin or "unknown")

        async with r.pipeline() as pipe:
            pipe.lrange(merchant_history_key, 0, risk_config["history_len"] - 1)
            pipe.lrange(pin_history_key, 0, risk_config["history_len"] - 1)
            res = await pipe.execute()

        merchant_history = [float(x) for x in res[0]]
        pin_history = [float(x) for x in res[1]]

        merchant_outlier, merchant_avg, merchant_std = vector_pulse.detect_amount_anomaly(
            merchant_history,
            amount,
            risk_config["z_score_threshold"],
        ) if len(merchant_history) >= 2 else (False, 0.0, 0.0)
        pin_outlier, pin_avg, pin_std = vector_pulse.detect_amount_anomaly(
            pin_history,
            amount,
            risk_config["z_score_threshold"],
        ) if len(pin_history) >= 2 else (False, 0.0, 0.0)

        async with r.pipeline() as pipe:
            pipe.lpush(merchant_history_key, amount)
            pipe.ltrim(merchant_history_key, 0, risk_config["history_len"] - 1)
            pipe.expire(merchant_history_key, 60 * 60 * 24 * 14)
            pipe.lpush(pin_history_key, amount)
            pipe.ltrim(pin_history_key, 0, risk_config["history_len"] - 1)
            pipe.expire(pin_history_key, 60 * 60 * 24 * 14)
            await pipe.execute()

        flagged = merchant_outlier or pin_outlier
        return flagged, {
            "merchant_outlier": merchant_outlier,
            "merchant_avg": merchant_avg,
            "merchant_std": merchant_std,
            "pin_outlier": pin_outlier,
            "pin_avg": pin_avg,
            "pin_std": pin_std,
            "merchant_history_size": len(merchant_history),
            "pin_history_size": len(pin_history),
        }
    except Exception as e:
        logging.error(f"Cohort Anomaly Check Failed: {e}")
        return False, {
            "merchant_outlier": False,
            "merchant_avg": 0.0,
            "merchant_std": 0.0,
            "pin_outlier": False,
            "pin_avg": 0.0,
            "pin_std": 0.0,
            "merchant_history_size": 0,
            "pin_history_size": 0,
        }

async def _check_ip_intelligence(ip: str) -> bool:
    """
    Detects if an IP is a proxy, VPN, or from a data center.
    Phase 12: Uses local GeoIP database for sub-10ms lookup, 
    falling back to external intelligence for specialized VPN flags.
    """
    if ip == "127.0.0.1": return False
    
    try:
        # 1. Check local Geolite2 for Geofencing (RTOs higher from non-IN IPs)
        match = GEO_READER.get(ip)
        is_risky_geo = False
        if match:
            country = match.get("country", {}).get("iso_code")
            if country and country != "IN":
                is_risky_geo = True # Higher risk if order is from outside India
        
        # 2. Check cache for any previously enriched VPN / hosting flags
        cache_key = f"ipint:{ip}"
        cached = await r.get(cache_key)
        if cached is not None:
            return cached == "1" or is_risky_geo

        # 3. No inline third-party lookup on the blocking path.
        return is_risky_geo
    except Exception as e:
        logging.error(f"IP Intelligence Lookup Failed for {ip}: {e}")
        return False


async def _log_risk_profile_change(email: str, actor: str, action: str, previous_config: dict, new_config: dict):
    try:
        await AUDIT_STORE.insert_risk_profile_audit(
            {
                "audit_id": secrets.token_hex(8),
                "email": email,
                "actor": actor,
                "action": action,
                "previous_config": json.dumps(previous_config),
                "new_config": json.dumps(new_config),
                "timestamp": time.time(),
            }
        )
    except Exception as e:
        logging.error(f"Risk profile audit logging failed: {e}")

async def _log_audit_event(risk_id: str, email: str, context: dict, decision: str, shadow: bool):
    try:
        await AUDIT_STORE.insert_risk_audit(
            {
                "risk_id": risk_id,
                "uid": context["uid"],
                "email": email,
                "risk_score": context["score"],
                "decision": decision,
                "shadow_mode": 1 if shadow else 0,
                "reasons": ",".join(context["flags"]),
                "metrics": json.dumps(
                    {
                        "metrics": context["metrics"],
                        "config": context.get("config", {}),
                    }
                ),
                "timestamp": context["timestamp"],
            }
        )
    except Exception as e:
        logging.error(f"Audit Logging Failed: {e}")

async def _get_trust_score(uid: str, merchant_key_hash: str | None) -> float:
    try:
        async with r.pipeline() as pipe:
            pipe.get(_merchant_state_key(merchant_key_hash, "repdelivered", uid))
            pipe.get(_merchant_state_key(merchant_key_hash, "reptotal", uid))
            res = await pipe.execute()
        
        delivered = int(res[0] or 0)
        total = int(res[1] or 0)
        return vector_pulse.calculate_trust_score(delivered, total)
    except Exception as e:
        logging.error(f"Trust Score Lookup Failed: {e}")
        return 50.0 # Neutral fallback


# ── Public Endpoints ───────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("landing/index.html")

@app.get("/admin", include_in_schema=False)
async def admin_portal():
    return FileResponse(
        "landing/admin.html",
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )


@app.get("/merchant", include_in_schema=False)
async def merchant_portal():
    return FileResponse(
        "landing/merchant.html",
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )


@app.get("/health")
async def health():
    redis_ok = False
    audit_ok = await AUDIT_STORE.healthcheck()

    try:
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if redis_ok and audit_ok else "degraded",
        "redis": "connected" if redis_ok else "unreachable",
        "audit": "connected" if audit_ok else "unreachable",
        "audit_backend": AUDIT_STORE.backend,
        "environment": ENVIRONMENT,
        "mode": "production" if redis_ok and audit_ok else "safe_fallback",
    }


@app.get("/readyz")
async def readiness():
    redis_ok = False
    audit_ok = await AUDIT_STORE.healthcheck()
    try:
        await r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    if not (redis_ok and audit_ok):
        raise HTTPException(
            status_code=503,
            detail={
                "redis": "connected" if redis_ok else "unreachable",
                "audit": "connected" if audit_ok else "unreachable",
                "audit_backend": AUDIT_STORE.backend,
            },
        )

    return {
        "status": "ready",
        "redis": "connected",
        "audit": "connected",
        "audit_backend": AUDIT_STORE.backend,
    }


# ── Admin: Issue API Keys  ─────────────────────────────────────────────────────
async def require_admin(request: Request, x_admin_key: str = Header(None)):
    # Legacy: Check static key
    if x_admin_key == ADMIN_KEY:
        return x_admin_key
        
    # Phase 14: Support Session-based Auth for Admin
    session_id = request.cookies.get("vp_session")
    if session_id:
        email = await r.get(f"session:{session_id}")
        if _is_admin_email(email):
            return email
            
    raise HTTPException(status_code=403, detail="Invalid admin credentials or session")


@app.post("/v1/admin/session", summary="Create an admin session")
async def create_admin_session(req: AdminSessionRequest, response: Response, request: Request):
    if req.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin credentials")

    await _create_session(PRIMARY_ADMIN_EMAIL, response, request)
    return {"message": "Admin session created"}


@app.post("/v1/admin/risk-config/{email}", summary="Update a user's merchant-specific risk profile")
async def update_risk_config(
    email: str,
    req: RiskConfigUpdateRequest,
    admin_actor: str = Depends(require_admin),
):
    key_hash = await _find_key_hash_by_email(email)
    if not key_hash:
        raise HTTPException(status_code=404, detail="User API key profile not found")

    existing_profile = await r.hgetall(f"apikey:{key_hash}")
    previous_config = _resolve_risk_config(existing_profile)
    payload = req.model_dump(exclude_none=True) if hasattr(req, "model_dump") else req.dict(exclude_none=True)

    updates = {}
    for name, value in payload.items():
        coerced = _validate_risk_value(name, _coerce_risk_value(name, value))
        updates[f"risk_{name}"] = str(coerced)

    if updates:
        await r.hset(f"apikey:{key_hash}", mapping=updates)

    profile = await r.hgetall(f"apikey:{key_hash}")
    new_config = _resolve_risk_config(profile)
    await _log_risk_profile_change(email, admin_actor, "UPDATE", previous_config, new_config)
    return {
        "email": email,
        "risk_profile": new_config,
        "is_custom": _has_custom_risk_profile(profile),
    }


@app.delete("/v1/admin/risk-config/{email}", summary="Reset a user's merchant-specific risk profile")
async def reset_risk_config(email: str, admin_actor: str = Depends(require_admin)):
    key_hash = await _find_key_hash_by_email(email)
    if not key_hash:
        raise HTTPException(status_code=404, detail="User API key profile not found")

    existing_profile = await r.hgetall(f"apikey:{key_hash}")
    previous_config = _resolve_risk_config(existing_profile)
    async with r.pipeline() as pipe:
        for name in RISK_CONFIG:
            pipe.hdel(f"apikey:{key_hash}", f"risk_{name}")
        await pipe.execute()

    profile = await r.hgetall(f"apikey:{key_hash}")
    new_config = _resolve_risk_config(profile)
    await _log_risk_profile_change(email, admin_actor, "RESET", previous_config, new_config)
    return {
        "email": email,
        "risk_profile": new_config,
        "is_custom": _has_custom_risk_profile(profile),
    }


@app.get("/v1/admin/risk-config-history/{email}", summary="List recent merchant risk profile changes")
async def get_risk_config_history(email: str, _: str = Depends(require_admin)):
    rows = await AUDIT_STORE.fetch_risk_profile_audits(email, limit=10)
    history = []
    for row in rows:
        history.append(
            {
                "audit_id": row["audit_id"],
                "email": row["email"],
                "actor": row["actor"],
                "action": row["action"],
                "timestamp": row["timestamp"],
                "previous_config": json.loads(row["previous_config"]) if row.get("previous_config") else {},
                "new_config": json.loads(row["new_config"]) if row.get("new_config") else {},
            }
        )
    return {"email": email, "history": history}


# ── Merchant: Self-Service ───────────────────────────────────────────────────
async def require_merchant_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    
    key_hash = _hash_key(api_key)
    key_data = await r.hgetall(f"apikey:{key_hash}")
    
    if not key_data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return {"key_hash": key_hash, "data": key_data, "email": key_data.get("email")}


@app.get("/v1/merchant/config", summary="Merchant: Fetch current risk profile")
async def get_merchant_config(merchant: dict = Depends(require_merchant_key)):
    profile = merchant["data"]
    config = _resolve_risk_config(profile)
    return {
        "email": merchant["email"],
        "risk_config": config,
        "is_custom": _has_custom_risk_profile(profile)
    }


@app.post("/v1/merchant/config", summary="Merchant: Update risk profile weights")
async def update_merchant_config(req: RiskConfigUpdateRequest, merchant: dict = Depends(require_merchant_key)):
    key_hash = merchant["key_hash"]
    existing_profile = merchant["data"]
    previous_config = _resolve_risk_config(existing_profile)
    
    payload = req.model_dump(exclude_none=True) if hasattr(req, "model_dump") else req.dict(exclude_none=True)
    
    updates = {}
    for name, value in payload.items():
        coerced = _validate_risk_value(name, _coerce_risk_value(name, value))
        updates[f"risk_{name}"] = str(coerced)

    if updates:
        await r.hset(f"apikey:{key_hash}", mapping=updates)

    profile = await r.hgetall(f"apikey:{key_hash}")
    new_config = _resolve_risk_config(profile)
    await _log_risk_profile_change(merchant["email"], f"merchant:{merchant['email']}", "UPDATE", previous_config, new_config)
    
    return {
        "email": merchant["email"],
        "risk_config": new_config,
        "is_custom": _has_custom_risk_profile(profile)
    }


@app.get("/v1/merchant/stats", summary="Merchant: Fetch usage and block stats")
async def get_merchant_stats(merchant: dict = Depends(require_merchant_key)):
    key_hash = merchant["key_hash"]
    key_data = merchant["data"]
    
    month_key = f"usage:{key_hash}:{time.strftime('%Y-%m')}"
    usage_val = await r.get(month_key)
    usage = int(usage_val or 0)
    
    plan = key_data.get("plan", "starter")
    limit = RATE_LIMITS.get(plan, RATE_LIMITS["starter"])
    
    # Block analytics and RTO savings
    # In a real app we'd query the audit store for this merchant's UID.
    # For now we simulate from the recently blocked orders if they match this merchant's UID
    # But since we don't have a reliable way to filter recently_blocked per merchant easily without full scan,
    # we return placeholder or aggregate if merchant email is known.
    
    # Implementation Note: In production we'd use merchant-specific counters in Redis.
    total_blocks_key = f"stats:blocks:{key_hash}"
    total_savings_key = f"stats:savings:{key_hash}"
    
    total_blocks = int(await r.get(total_blocks_key) or 0)
    total_savings = int(await r.get(total_savings_key) or 0)
    
    return {
        "email": merchant["email"],
        "usage_this_month": usage,
        "limit": limit,
        "plan": plan,
        "total_blocks": total_blocks,
        "total_savings_inr": total_savings,
        "recent_activity": [] # We could populate this from AUDIT_STORE or specialized redis list
    }

@app.get("/v1/admin/users", summary="List all registered API keys and their usage")
async def get_all_users(_: str = Depends(require_admin)):
    keys = await r.smembers("admin:all_keys")
    users = []
    current_month = time.strftime('%Y-%m')
    for key_hash in keys:
        try:
            async with r.pipeline() as pipe:
                pipe.hgetall(f"apikey:{key_hash}")
                pipe.get(f"usage:{key_hash}:{current_month}")
                res = await pipe.execute()
                
            key_data = res[0]
            if not key_data: continue
                
            email = key_data.get("email", "unknown")
            
            # Phase 15: Hide Admin from User Registry for Privacy
            if _is_admin_email(email):
                continue

            usage = int(res[1] or 0)
            
            # Retrieve the API key from B2C profile if not in apikey profile
            api_key = key_data.get("api_key")
            api_key_preview = key_data.get("api_key_preview") or _key_preview(
                key_data.get("key_prefix"),
                key_data.get("key_suffix"),
            )

            users.append({
                "email": email,
                "api_key_preview": api_key_preview,
                "plan": key_data.get("plan", "free"),
                "created_at": key_data.get("created_at", "unknown"),
                "usage_this_month": usage,
                "limit": RATE_LIMITS.get(key_data.get("plan", "free"), 1_000),
                "risk_profile": _resolve_risk_config(key_data),
                "is_custom_risk_profile": _has_custom_risk_profile(key_data),
            })
        except Exception:
            continue
            
    users.sort(key=lambda x: x["usage_this_month"], reverse=True)
    total_savings = int(await r.get("total_savings_inr") or 0)
    recent_blocks = await r.lrange("recent_blocks", 0, 49)
    return {
        "users": users,
        "total_users": len(users),
        "savings": total_savings,
        "recent_blocks": recent_blocks,
    }


@app.get("/v1/admin/pilot-requests", summary="List recent pilot requests from the landing page")
async def get_pilot_requests(_: str = Depends(require_admin)):
    emails = await r.smembers("pilot_request_emails")
    requests = []
    for email in emails:
        payload = await r.hgetall(f"pilot_request:{email}")
        if payload:
            requests.append(payload)
    requests.sort(key=lambda item: float(item.get("submitted_at", 0)), reverse=True)
    requests = requests[:50]
    return {
        "requests": requests,
        "total": len(requests),
    }


@app.get("/v1/admin/pilot-analytics", summary="Summarize pilot lead funnel and mix")
async def get_pilot_analytics(_: str = Depends(require_admin)):
    emails = await r.smembers("pilot_request_emails")
    leads = []
    for email in emails:
        payload = await r.hgetall(f"pilot_request:{email}")
        if payload:
            leads.append(payload)

    status_counts = {
        "new": 0,
        "contacted": 0,
        "pilot_started": 0,
        "won": 0,
        "closed": 0,
    }
    category_counts: dict[str, int] = {}
    cod_band_counts: dict[str, int] = {}
    owner_counts: dict[str, int] = {}

    for lead in leads:
        status = lead.get("status", "new")
        if status in status_counts:
            status_counts[status] += 1
        category = (lead.get("category") or "Unknown").strip() or "Unknown"
        cod_band = (lead.get("cod_share") or "Unknown").strip() or "Unknown"
        owner = (lead.get("assigned_to") or "Unassigned").strip() or "Unassigned"
        category_counts[category] = category_counts.get(category, 0) + 1
        cod_band_counts[cod_band] = cod_band_counts.get(cod_band, 0) + 1
        owner_counts[owner] = owner_counts.get(owner, 0) + 1

    def _top_items(values: dict[str, int], limit: int = 3) -> list[dict[str, Any]]:
        return [
            {"label": label, "count": count}
            for label, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))[:limit]
        ]

    total = len(leads)
    return {
        "total": total,
        "funnel": {
            **status_counts,
            "active_pipeline": status_counts["new"] + status_counts["contacted"] + status_counts["pilot_started"],
            "conversion_rate": round((status_counts["won"] / total) * 100, 1) if total else 0.0,
        },
        "top_categories": _top_items(category_counts),
        "top_cod_bands": _top_items(cod_band_counts),
        "owner_load": _top_items(owner_counts),
    }


@app.get("/v1/admin/upgrade-requests", summary="List merchant upgrade requests")
async def get_upgrade_requests(_: str = Depends(require_admin)):
    emails = await r.smembers("upgrade_request_emails")
    requests = []
    for email in emails:
        payload = await r.hgetall(f"upgrade_request:{email}")
        if payload:
            requests.append(payload)
    requests.sort(key=lambda item: float(item.get("submitted_at", 0)), reverse=True)
    requests = requests[:50]
    return {
        "requests": requests,
        "total": len(requests),
    }


@app.get("/v1/admin/business-metrics", summary="Summarize core business metrics for the admin dashboard")
async def get_business_metrics(_: str = Depends(require_admin)):
    current_month = time.strftime("%Y-%m")
    keys = await r.smembers("admin:all_keys")
    active_merchants = 0
    total_api_calls = 0
    paid_merchants = 0

    for key_hash in keys:
        key_data = await r.hgetall(f"apikey:{key_hash}")
        if not key_data:
            continue
        email = key_data.get("email", "")
        if _is_admin_email(email):
            continue
        active_merchants += 1
        if key_data.get("plan", "free") != "free":
            paid_merchants += 1
        total_api_calls += int(await r.get(f"usage:{key_hash}:{current_month}") or 0)

    pilot_requests = int(await r.scard("pilot_request_emails") or 0)
    upgrade_requests = int(await r.scard("upgrade_request_emails") or 0)
    total_savings = int(await r.get("total_savings_inr") or 0)
    velocity_hits = int(await r.get("stat:velocity") or 0)
    sybil_hits = int(await r.get("stat:sybil") or 0)
    anomaly_hits = int(await r.get("stat:price") or 0)
    vpn_hits = int(await r.get("stat:vpn") or 0)

    return {
        "active_merchants": active_merchants,
        "paid_merchants": paid_merchants,
        "monthly_api_calls": total_api_calls,
        "pilot_requests": pilot_requests,
        "upgrade_requests": upgrade_requests,
        "total_savings_inr": total_savings,
        "risk_signal_counts": {
            "velocity": velocity_hits,
            "sybil": sybil_hits,
            "anomaly": anomaly_hits,
            "vpn": vpn_hits,
        },
    }


@app.post("/v1/admin/upgrade-requests/{email}/status", summary="Approve or reject an upgrade request")
async def update_upgrade_request_status(
    email: str,
    req: UpgradeRequestDecision,
    admin_actor: str = Depends(require_admin),
):
    normalized_email = email.strip().lower()
    request_key = f"upgrade_request:{normalized_email}"
    existing = await r.hgetall(request_key)
    if not existing:
        raise HTTPException(status_code=404, detail="Upgrade request not found")

    requested_plan = existing.get("requested_plan")
    if requested_plan not in RATE_LIMITS:
        raise HTTPException(status_code=400, detail="Requested plan is invalid")

    updates = {
        "status": req.status,
        "reviewed_at": str(time.time()),
        "reviewed_by": admin_actor,
    }

    async with r.pipeline() as pipe:
        pipe.hset(request_key, mapping=updates)
        if req.status == "approved":
            pipe.hset(f"user:{normalized_email}", mapping={"plan": requested_plan})
            key_hash = await _find_key_hash_by_email(normalized_email)
            if key_hash:
                pipe.hset(f"apikey:{key_hash}", mapping={"plan": requested_plan})
        await pipe.execute()

    updated = await r.hgetall(request_key)
    _log_event(
        "upgrade_request_reviewed",
        email=normalized_email,
        requested_plan=requested_plan,
        status=req.status,
        actor=admin_actor,
    )
    return {
        "status": "success",
        "request": updated,
    }


@app.post("/v1/admin/pilot-requests/{email}/status", summary="Update pilot request status")
async def update_pilot_request_status(
    email: str,
    req: PilotRequestStatusUpdate,
    admin_actor: str = Depends(require_admin),
):
    normalized_email = email.strip().lower()
    key = f"pilot_request:{normalized_email}"
    existing = await r.hgetall(key)
    if not existing:
        raise HTTPException(status_code=404, detail="Pilot request not found")

    await r.hset(
        key,
        mapping={
            "status": req.status,
            "updated_at": str(time.time()),
            "updated_by": admin_actor,
        },
    )
    updated = await r.hgetall(key)
    _log_event(
        "pilot_request_status_updated",
        email=normalized_email,
        status=req.status,
        actor=admin_actor,
    )
    return {
        "status": "success",
        "request": updated,
    }


@app.post("/v1/admin/pilot-requests/{email}/details", summary="Update lead owner and notes")
async def update_pilot_request_details(
    email: str,
    req: PilotRequestDetailUpdate,
    admin_actor: str = Depends(require_admin),
):
    normalized_email = email.strip().lower()
    key = f"pilot_request:{normalized_email}"
    existing = await r.hgetall(key)
    if not existing:
        raise HTTPException(status_code=404, detail="Pilot request not found")

    updates = {
        "updated_at": str(time.time()),
        "updated_by": admin_actor,
    }
    if req.assigned_to is not None:
        updates["assigned_to"] = req.assigned_to.strip()
    if req.notes is not None:
        updates["notes"] = req.notes.strip()

    await r.hset(key, mapping=updates)
    updated = await r.hgetall(key)
    _log_event(
        "pilot_request_details_updated",
        email=normalized_email,
        actor=admin_actor,
        assigned_to=updates.get("assigned_to", existing.get("assigned_to", "")),
    )
    return {
        "status": "success",
        "request": updated,
    }

@app.delete("/v1/admin/user/{email}", summary="Purge a user account and all associated data")
async def delete_user(email: str, _: str = Depends(require_admin)):
    # 1. Get user data to find the API key
    user_profile = await r.hgetall(f"user:{email}")
    key_hash = user_profile.get("key_hash") or await _find_key_hash_by_email(email)

    usage_keys = await r.smembers(f"usage_index:{key_hash}") if key_hash else set()
    risk_ids = await r.smembers(f"risk_index:{email}")
    session_ids = await r.smembers(f"session_index:{email}")
    seen_uids = await r.smembers(f"user_uids:{email}")
    addr_keys = await r.smembers(f"addr_index:{email}")

    async with r.pipeline() as pipe:
        pipe.delete(f"user:{email}")
        pipe.delete(f"emailkey:{email}")
        if key_hash:
            pipe.delete(f"apikey:{key_hash}")
            pipe.srem("admin:all_keys", key_hash)
            pipe.delete(f"usage_index:{key_hash}")
            for usage_key in usage_keys:
                pipe.delete(usage_key)
        for session_id in session_ids:
            pipe.delete(f"session:{session_id}")
        pipe.delete(f"session_index:{email}")
        for uid in seen_uids:
            pipe.delete(_merchant_state_key(key_hash, "repdelivered", uid))
            pipe.delete(_merchant_state_key(key_hash, "reptotal", uid))
            pipe.delete(_merchant_state_key(key_hash, "history", uid))
            pipe.delete(_merchant_state_key(key_hash, "velocity", uid))
        pipe.delete(f"user_uids:{email}")
        for addr_key in addr_keys:
            pipe.delete(addr_key)
        pipe.delete(f"addr_index:{email}")
        for risk_id in risk_ids:
            pipe.delete(f"explain:{risk_id}")
        pipe.delete(f"risk_index:{email}")
        
        # Comprehensive purge
        pipe.delete(f"savings:{email}")
        await pipe.execute()

    await AUDIT_STORE.delete_user_audits(email)
    
    return {"status": "success", "message": f"User {email} and associated data purged."}

@app.post("/v1/register", summary="Issue an API key (admin only)")
async def register(req: RegisterRequest):
    if req.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    if req.plan not in RATE_LIMITS:
        raise HTTPException(status_code=400, detail=f"Plan must be one of: {list(RATE_LIMITS)}")

    raw_key = f"vp_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    key_hash = key_meta["key_hash"]

    async with r.pipeline() as pipe:
        pipe.hset(
            f"apikey:{key_hash}",
            mapping={
                "email": req.email,
                "plan": req.plan,
                "key_prefix": key_meta["key_prefix"],
                "key_suffix": key_meta["key_suffix"],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        pipe.sadd("admin:all_keys", key_hash)
        pipe.set(f"emailkey:{req.email}", key_hash)
        await pipe.execute()

    return {
        "api_key": raw_key,
        "plan": req.plan,
        "monthly_limit": RATE_LIMITS[req.plan],
        "note": "Store this key safely. It will not be shown again.",
    }

@app.post("/v1/public/request-free-key", summary="Issue a free tier API key instantly")
async def request_free_key(req: PublicRegisterRequest, request: Request):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
    
    if await r.get(f"ratelimit:ip:{client_ip}"):
         raise HTTPException(status_code=429, detail="Only one free key allowed per day per IP.")

    raw_key = f"vp_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    key_hash = key_meta["key_hash"]

    async with r.pipeline() as pipe:
        pipe.setex(f"ratelimit:ip:{client_ip}", 86400, "1")
        pipe.hset(
            f"apikey:{key_hash}",
            mapping={
                "email": req.email,
                "plan": "free",
                "key_prefix": key_meta["key_prefix"],
                "key_suffix": key_meta["key_suffix"],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        pipe.sadd("admin:all_keys", key_hash)
        pipe.set(f"emailkey:{req.email}", key_hash)
        await pipe.execute()

    return {
        "api_key": raw_key,
        "plan": "free",
        "monthly_limit": RATE_LIMITS["free"],
        "note": "Store this test key safely. It will not be shown again.",
        "dashboard_url": "/merchant"
    }


@app.post("/v1/public/request-pilot", summary="Capture a pilot request from the landing page")
async def request_pilot(req: PilotRequest, request: Request):
    submitted_at = time.time()
    client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
    key = f"pilot_request:{req.email.lower()}"
    payload = {
        "name": req.name.strip(),
        "email": req.email.strip().lower(),
        "company": req.company.strip(),
        "category": req.category.strip(),
        "monthly_orders": req.monthly_orders.strip(),
        "cod_share": req.cod_share.strip(),
        "status": "new",
        "assigned_to": "",
        "notes": "",
        "submitted_at": str(submitted_at),
        "source": "landing_page",
        "ip": client_ip,
    }

    async with r.pipeline() as pipe:
        pipe.hset(key, mapping=payload)
        pipe.sadd("pilot_request_emails", payload["email"])
        pipe.lpush("pilot_requests", json.dumps(payload))
        pipe.ltrim("pilot_requests", 0, 199)
        await pipe.execute()

    _log_event(
        "pilot_request_created",
        email=payload["email"],
        company=payload["company"],
        category=payload["category"],
    )
    await _send_pilot_request_webhook(payload)
    return {
        "status": "success",
        "message": "Pilot request received. We will reach out shortly.",
    }

# ── User Auth (B2C) ────────────────────────────────────────────────────────────
def _hash_password(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return key.hex()

@app.post("/v1/auth/signup", summary="Create a new user account")
async def auth_signup(req: AuthRequest, response: Response, request: Request):
    # Phase 15: Reserve Admin Email exclusively
    if _is_admin_email(req.email):
        raise HTTPException(status_code=403, detail="Sovereign Identity Reserved")

    if await r.hexists(f"user:{req.email}", "pwd_hash"):
        raise HTTPException(status_code=400, detail="Email already registered")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(req.password, salt)
    
    # Generate API key
    raw_key = f"vp_live_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    key_hash = key_meta["key_hash"]

    async with r.pipeline() as pipe:
        # Store User
        pipe.hset(f"user:{req.email}", mapping={
            "pwd_hash": pwd_hash,
            "salt": salt,
            "key_hash": key_hash,
            "key_prefix": key_meta["key_prefix"],
            "key_suffix": key_meta["key_suffix"],
            "plan": "free",
        })
        # Store API Key Profile
        pipe.hset(f"apikey:{key_hash}", mapping={
            "email": req.email,
            "plan": "free",
            "key_prefix": key_meta["key_prefix"],
            "key_suffix": key_meta["key_suffix"],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        pipe.sadd("admin:all_keys", key_hash)
        pipe.set(f"emailkey:{req.email}", key_hash)
        await pipe.execute()
    
    await _create_session(req.email, response, request)
    
    return {"message": "Account created successfully", "api_key": raw_key}

@app.post("/v1/auth/login", summary="Log in to an existing account")
async def auth_login(req: AuthRequest, response: Response, request: Request):
    user_data = await r.hgetall(f"user:{req.email}")
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    pwd_hash = _hash_password(req.password, user_data["salt"])
    if pwd_hash != user_data["pwd_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    await _create_session(req.email, response, request)
    
    return {"message": "Logged in successfully"}

@app.post("/v1/auth/logout", summary="End the current session")
async def auth_logout(request: Request, response: Response):
    session_id = request.cookies.get("vp_session")
    if session_id:
        email = await r.get(f"session:{session_id}")
        async with r.pipeline() as pipe:
            pipe.delete(f"session:{session_id}")
            if email:
                pipe.srem(f"session_index:{email}", session_id)
            await pipe.execute()
    response.delete_cookie("vp_session")
    return {"message": "Logged out successfully"}

@app.get("/v1/auth/me", summary="Get the current logged in user's profile and API key")
async def auth_me(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")
        
    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Fetch detailed metrics for the Signal Hub using an async pipeline
    current_month = time.strftime('%Y-%m')
    key_hash = user_data.get("key_hash") or await _find_key_hash_by_email(email)
    preview = _key_preview(user_data.get("key_prefix"), user_data.get("key_suffix"))
    if preview == "REDACTED" and key_hash:
        key_profile = await r.hgetall(f"apikey:{key_hash}")
        preview = _key_preview(key_profile.get("key_prefix"), key_profile.get("key_suffix"))
    async with r.pipeline() as pipe:
        pipe.get(f"usage:{key_hash}:{current_month}" if key_hash else "usage:missing")
        pipe.get(f"savings:{email}")
        res = await pipe.execute()
    
    usage = int(res[0] or 0)
    savings = float(res[1] or 0)
    plan = user_data.get("plan", "free")
    limit = RATE_LIMITS.get(plan, 1000)

    # We never return passwords or salts.
    return {
        "email": email,
        "api_key": preview,
        "is_admin": _is_admin_email(email),
        "risk_profile": _resolve_risk_config(await r.hgetall(f"apikey:{key_hash}")) if key_hash else dict(RISK_CONFIG),
        "metrics": {
            "usage": usage,
            "limit": limit,
            "savings": savings,
            "plan": plan.upper(),
            "pct": min(100, round((usage / limit) * 100)) if limit > 0 else 0
        }
    }


@app.get("/v1/auth/reporting", summary="Get merchant-facing reporting for the Signal Hub")
async def auth_reporting(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    current_month = time.strftime("%Y-%m")
    key_hash = user_data.get("key_hash") or await _find_key_hash_by_email(email)
    async with r.pipeline() as pipe:
        pipe.get(f"usage:{key_hash}:{current_month}" if key_hash else "usage:missing")
        pipe.get(f"savings:{email}")
        res = await pipe.execute()

    usage = int(res[0] or 0)
    savings = float(res[1] or 0)
    recent_rows = await AUDIT_STORE.fetch_recent_risk_audits(email, limit=12)

    factor_counts: dict[str, int] = {}
    summary = {
        "screened_this_month": usage,
        "estimated_savings_inr": savings,
        "recent_force_prepaid": 0,
        "recent_allow_cod": 0,
        "recent_rto": 0,
        "recent_fraud_confirmed": 0,
    }
    recent_decisions = []

    for row in recent_rows:
        decision = row.get("decision") or "ALLOW_COD"
        outcome = row.get("outcome") or "PENDING"
        if decision == "FORCE_PREPAID":
            summary["recent_force_prepaid"] += 1
        else:
            summary["recent_allow_cod"] += 1
        if outcome == "RTO":
            summary["recent_rto"] += 1
        elif outcome == "FRAUD_CONFIRMED":
            summary["recent_fraud_confirmed"] += 1

        flags = [flag for flag in (row.get("reasons") or "").split(",") if flag]
        for flag in flags:
            factor_counts[flag] = factor_counts.get(flag, 0) + 1

        recent_decisions.append(
            {
                "risk_id": row.get("risk_id"),
                "uid": row.get("uid"),
                "score": round(float(row.get("risk_score") or 0), 1),
                "decision": decision,
                "flags": flags,
                "outcome": outcome,
                "timestamp": row.get("timestamp"),
            }
        )

    top_factors = [
        {"label": label, "count": count}
        for label, count in sorted(factor_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]

    return {
        "summary": summary,
        "top_factors": top_factors,
        "recent_decisions": recent_decisions,
    }


@app.get("/v1/auth/settings", summary="Get merchant account settings")
async def auth_settings(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "email": email,
        "settings": {
            "company_name": user_data.get("company_name", ""),
            "category": user_data.get("category", ""),
            "monthly_orders": user_data.get("monthly_orders", ""),
            "cod_share": user_data.get("cod_share", ""),
        },
    }


@app.post("/v1/auth/settings", summary="Update merchant account settings")
async def update_auth_settings(update: MerchantSettingsUpdate, request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_key = f"user:{email}"
    user_data = await r.hgetall(user_key)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    fields = {}
    if update.company_name is not None:
        fields["company_name"] = update.company_name.strip()
    if update.category is not None:
        fields["category"] = update.category.strip()
    if update.monthly_orders is not None:
        fields["monthly_orders"] = update.monthly_orders.strip()
    if update.cod_share is not None:
        fields["cod_share"] = update.cod_share.strip()

    if fields:
        await r.hset(user_key, mapping=fields)

    return {
        "status": "success",
        "settings": {
            "company_name": fields.get("company_name", user_data.get("company_name", "")),
            "category": fields.get("category", user_data.get("category", "")),
            "monthly_orders": fields.get("monthly_orders", user_data.get("monthly_orders", "")),
            "cod_share": fields.get("cod_share", user_data.get("cod_share", "")),
        },
    }


@app.post("/v1/auth/upgrade-request", summary="Request a paid plan upgrade")
async def request_upgrade(req: UpgradeRequest, request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    user_data = await r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    payload = {
        "email": email,
        "current_plan": user_data.get("plan", "free"),
        "requested_plan": req.requested_plan,
        "note": (req.note or "").strip(),
        "status": "submitted",
        "submitted_at": str(time.time()),
    }
    await r.hset(f"upgrade_request:{email}", mapping=payload)
    await r.sadd("upgrade_request_emails", email)
    _log_event(
        "upgrade_request_created",
        email=email,
        current_plan=payload["current_plan"],
        requested_plan=req.requested_plan,
    )
    return {
        "status": "success",
        "request": payload,
    }


@app.get("/v1/auth/upgrade-request", summary="Get the current merchant upgrade request")
async def get_upgrade_request(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = await r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")

    payload = await r.hgetall(f"upgrade_request:{email}")
    return {
        "request": payload or None,
    }

# ── Core: Risk Check ───────────────────────────────────────────────────────────
@app.post("/v1/risk-check", summary="Evaluate an order for fraud risk")
async def check_order(order: Order, key_data: dict = Depends(require_api_key)):
    start_time = time.perf_counter()
    uid, amount, address, client_ip = order.uid, order.amt, order.addr, order.ip
    reasons = []
    risk_config = _resolve_risk_config(key_data)
    merchant_key_hash = key_data.get("key_hash")
    merchant_email = key_data.get("email")

    # Concurrent checks using pipelining and async execution
    import asyncio
    
    # 1. Parallel Data Fetch and Internal Processing
    velocity_task = _check_velocity(uid, risk_config, merchant_key_hash)
    sybil_task = _check_sybil(uid, address, risk_config, merchant_key_hash, merchant_email)
    price_task = _check_price_anomaly(uid, amount, risk_config, merchant_key_hash)
    trust_task = _get_trust_score(uid, merchant_key_hash)
    ip_task = _check_ip_intelligence(client_ip)
    
    global_velocity_task = _check_global_velocity(client_ip, risk_config)
    global_sybil_task = _check_global_sybil(uid, address, risk_config)
    device_velocity_task = _check_device_velocity(uid, order.device_hash, risk_config)
    geo_velocity_task = _check_geo_velocity(uid, client_ip, order.device_hash, risk_config)

    try:
        is_gibberish_flag = vector_pulse.is_gibberish_address(address)
    except Exception:
        is_gibberish_flag = False

    try:
        is_suspicious_name_flag = vector_pulse.is_suspicious_name(order.name or "")
    except Exception:
        is_suspicious_name_flag = False
        
    try:
        is_suspicious_phone_flag = vector_pulse.is_suspicious_phone(order.phone or "")
    except Exception:
        is_suspicious_phone_flag = False

    is_time_anomaly_flag = _check_time_anomaly()
    is_bot_speed_flag = _check_bot_speed(order.checkout_time_secs)
    is_disposable_email_flag = _check_disposable_email(order.email)
    
    try:
        is_email_name_mismatch_flag = vector_pulse.is_email_name_mismatch(order.name or "", order.email or "")
    except Exception:
        is_email_name_mismatch_flag = False
        
    try:
        is_poor_address_flag = vector_pulse.has_poor_address_structure(address)
    except Exception:
        is_poor_address_flag = False

    high_risk_pin_task = _check_high_risk_pin(order.pin)

    results = await asyncio.gather(
        velocity_task, sybil_task, price_task, trust_task, ip_task,
        global_velocity_task, global_sybil_task, device_velocity_task, geo_velocity_task, high_risk_pin_task
    )
    
    is_velocity_flag, is_sybil_flag, (is_price_anomaly, avg, std_dev), trust_score, is_vpn_flag, is_global_velocity_flag, is_global_sybil_flag, is_device_velocity_flag, is_geo_velocity_flag, is_high_risk_pin_flag = results
    
    is_global_network_flag = is_global_velocity_flag or is_global_sybil_flag

    # 2. Configurable risk scoring
    risk_score = _calculate_risk_score(
        velocity_flag=is_velocity_flag,
        sybil_flag=is_sybil_flag,
        anomaly_flag=is_price_anomaly,
        identity_flag=False,
        cohort_flag=False,
        trust_score=trust_score,
        vpn_flag=is_vpn_flag,
        global_network_flag=is_global_network_flag,
        gibberish_flag=is_gibberish_flag,
        device_velocity_flag=is_device_velocity_flag,
        suspicious_name_flag=is_suspicious_name_flag,
        geo_velocity_flag=is_geo_velocity_flag,
        time_anomaly_flag=is_time_anomaly_flag,
        bot_speed_flag=is_bot_speed_flag,
        suspicious_phone_flag=is_suspicious_phone_flag,
        disposable_email_flag=is_disposable_email_flag,
        email_name_mismatch_flag=is_email_name_mismatch_flag,
        poor_address_flag=is_poor_address_flag,
        high_risk_pin_flag=is_high_risk_pin_flag,
        risk_config=risk_config,
    )

    if is_velocity_flag: reasons.append("HIGH_VELOCITY")
    if is_sybil_flag:    reasons.append("ADDRESS_SYBIL_DETECTED")
    if is_price_anomaly: reasons.append("HIGH_DEVIATION")
    if is_vpn_flag:      reasons.append("ANONYMOUS_IP_DETECTED")
    if is_global_network_flag: reasons.append("GLOBAL_CONSORTIUM_BLOCK")
    if is_gibberish_flag: reasons.append("GIBBERISH_ADDRESS")
    if is_device_velocity_flag: reasons.append("DEVICE_FINGERPRINT_VELOCITY")
    if is_suspicious_name_flag: reasons.append("SUSPICIOUS_NAME")
    if is_geo_velocity_flag: reasons.append("IMPOSSIBLE_TRAVEL")
    if is_time_anomaly_flag: reasons.append("TIME_OF_DAY_ANOMALY")
    if is_bot_speed_flag: reasons.append("BOT_SPEED_CHECKOUT")
    if is_suspicious_phone_flag: reasons.append("SUSPICIOUS_PHONE")
    if is_disposable_email_flag: reasons.append("DISPOSABLE_EMAIL")
    if is_email_name_mismatch_flag: reasons.append("EMAIL_NAME_MISMATCH")
    if is_poor_address_flag: reasons.append("POOR_ADDRESS_STRUCTURE")
    if is_high_risk_pin_flag: reasons.append("HIGH_RISK_PIN")
    if trust_score < risk_config["trust_floor"] and trust_score != 50.0:
        reasons.append("LOW_TRUST_SCORE")

    # Decision threshold logic
    is_risky = risk_score > risk_config["decision_threshold"]
    # Shadow Mode: Evaluate but never block
    is_blocked = is_risky and not order.shadow
    action = "FORCE_PREPAID" if is_blocked else "ALLOW_COD"
    risk_id = secrets.token_hex(8)

    # 3. Update Stats & Persistent Audit
    try:
        context = {
            "uid": uid,
            "score": float(risk_score),
            "flags": reasons,
            "metrics": {
                "velocity": is_velocity_flag,
                "sybil": is_sybil_flag,
                "price": is_price_anomaly,
                "trust": float(trust_score),
                "vpn": is_vpn_flag,
                "global_network": is_global_network_flag,
                "gibberish": is_gibberish_flag,
                "device_velocity": is_device_velocity_flag,
                "suspicious_name": is_suspicious_name_flag,
                "geo_velocity": is_geo_velocity_flag,
                "time_anomaly": is_time_anomaly_flag,
                "bot_speed": is_bot_speed_flag,
                "suspicious_phone": is_suspicious_phone_flag,
                "disposable_email": is_disposable_email_flag,
                "email_name_mismatch": is_email_name_mismatch_flag,
                "poor_address": is_poor_address_flag,
                "high_risk_pin": is_high_risk_pin_flag,
            },
            "config": risk_config,
            "timestamp": time.time()
        }
        
        # Async background logging (simulated by await here for reliability)
        await _log_audit_event(risk_id, key_data.get("email"), context, action, order.shadow)

        async with r.pipeline() as pipe:
            pipe.setex(f"explain:{risk_id}", 86400 * 3, json.dumps(context)) # 3 day high-speed cache
            pipe.sadd(f"risk_index:{key_data.get('email')}", risk_id)
            pipe.sadd(f"user_uids:{key_data.get('email')}", uid)
            if is_risky:
                pipe.incrby("total_savings_inr", risk_config["savings_per_block_inr"])
                
                # Merchant specific savings
                pipe.incrby(f"stats:savings:{merchant_key_hash}", risk_config["savings_per_block_inr"])
                pipe.incr(f"stats:blocks:{merchant_key_hash}")

                status_label = "SHADOW_BLOCK" if order.shadow else "BLOCK"
                pipe.lpush("recent_blocks", f"{uid}: {', '.join(reasons)} ({status_label}: {risk_score:.0f}) [ID: {risk_id}]")
                pipe.ltrim("recent_blocks", 0, 49)
            
            if is_velocity_flag: pipe.incr("stat:velocity")
            if is_sybil_flag: pipe.incr("stat:sybil")
            if is_price_anomaly: pipe.incr("stat:price")
            if is_vpn_flag: pipe.incr("stat:vpn")
            
            pipe.incr(_merchant_state_key(merchant_key_hash, "reptotal", uid))
            await pipe.execute()
    except Exception as e:
        logging.warning(f"Stats update failed: {e}")

    latency = (time.perf_counter() - start_time) * 1000
    return {
        "uid": uid,
        "risk_id": risk_id,
        "decision": action,
        "shadow_mode": order.shadow,
        "risk_score": round(float(risk_score), 1),
        "risk_factors": reasons,
        "latency_ms": f"{latency:.2f}ms",
    }


# ── Reputation Feedback ────────────────────────────────────────────────────────
@app.post("/v1/order-delivered", summary="Mark order as delivered — builds user trust")
async def mark_delivered(uid: str, key_data: dict = Depends(require_api_key)):
    try:
        merchant_key_hash = key_data.get("key_hash")
        async with r.pipeline() as pipe:
            pipe.incr(_merchant_state_key(merchant_key_hash, "repdelivered", uid))
            pipe.incr(_merchant_state_key(merchant_key_hash, "reptotal", uid))
            await pipe.execute()
        return {"uid": uid, "trust_score": round(await _get_trust_score(uid, merchant_key_hash), 1), "status": "updated"}
    except Exception as e:
        logging.error(f"Failed to update delivery rep: {e}")
        return {"uid": uid, "status": "failed", "reason": "DB unreachable"}

# ── Observability: Explain Decisions ──────────────────────────────────────────
@app.get("/v1/explain/{risk_id}", summary="Get human-readable reasoning for a fraud decision")
async def explain_decision(risk_id: str, key_data: dict = Depends(require_api_key_or_admin)):
    try:
        raw_data = await r.get(f"explain:{risk_id}")
        if not raw_data:
            # Fallback to persistent DB if Redis cache expired
            row = await AUDIT_STORE.fetch_risk_audit(risk_id)
            if not row:
                raise HTTPException(status_code=404, detail="Risk ID not found")
            payload = json.loads(row["metrics"])
            if "metrics" in payload:
                metrics = payload["metrics"]
                config = payload.get("config", dict(RISK_CONFIG))
            else:
                metrics = payload
                config = dict(RISK_CONFIG)
            context = {
                "score": row["risk_score"],
                "flags": row["reasons"].split(",") if row["reasons"] else [],
                "metrics": metrics,
                "config": config,
                "timestamp": row["timestamp"]
            }
        else:
            context = json.loads(raw_data)
        
        # Build explanation
        narrative = []
        m = context["metrics"]
        config = context.get("config", dict(RISK_CONFIG))
        if m["velocity"]: narrative.append(
            f"Multiple orders ({config['velocity_max_orders']}+) detected in "
            f"{config['velocity_window_secs']}s window."
        )
        if m["vpn"]:      narrative.append("Transaction attempted via Data Center or Anonymous Proxy (VPN).")
        if m["price"]:    narrative.append("Transaction amount significantly deviates from historical average.")
        if m["sybil"]:    narrative.append("Multiple UIDs linked to same delivery address.")
        if m.get("trust", 50.0) < config["trust_floor"]:
            narrative.append(f"Customer has low delivery score ({m['trust']:.0f}% success).")
        
        return {
            "risk_id": risk_id,
            "score": context["score"],
            "decision": (
                "FORCE_PREPAID"
                if context["score"] > config["decision_threshold"]
                else "ALLOW_COD"
            ),
            "findings": narrative,
            "raw_metrics": m,
            "timestamp": context["timestamp"]
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise
        logging.error(f"Explain API Error: {e}")
        raise HTTPException(status_code=500, detail="Internal analysis service error")

# ── Feedback Loop: Update Outcome ─────────────────────────────────────────────
class OutcomeUpdate(BaseModel):
    risk_id: str
    status: Literal["DELIVERED", "RTO", "FRAUD_CONFIRMED"]

@app.post("/v1/outcome", summary="Report the final outcome of a transaction (ML Feedback Loop)")
async def update_outcome(update: OutcomeUpdate, key_data: dict = Depends(require_api_key)):
    try:
        await AUDIT_STORE.update_outcome(update.risk_id, update.status)
        return {"status": "success", "risk_id": update.risk_id, "updated_to": update.status}
    except Exception as e:
        logging.error(f"Outcome update failed: {e}")
        raise HTTPException(status_code=500, detail="Persistence layer error")
