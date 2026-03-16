import os
import json
import logging
import hashlib
import time
import secrets
from typing import Any
from fastapi import Request, Response, HTTPException
from app.core.redis import r
from app.db.database import AUDIT_STORE
from app.core.config import RISK_CONFIG, RISK_CONFIG_BOUNDS, RISK_CONFIG_TYPES, ADMIN_KEY, SESSION_COOKIE_SECURE

ADMIN_EMAILS = [
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "admin@vantix.ai").split(",")
    if email.strip()
]
PRIMARY_ADMIN_EMAIL = ADMIN_EMAILS[0] if ADMIN_EMAILS else "admin@vantix.ai"

# Lua Script for Atomic Sliding Window Rate Limiting
LUA_RATE_LIMIT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local clear_before = now - window

redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, ARGV[4])
    redis.call('EXPIRE', key, window * 2)
    return 0
else
    return 1
end
"""

async def _sliding_window_rate_limit(key: str, limit: int, window_secs: int) -> bool:
    """Returns True if the rate limit is exceeded."""
    try:
        # returns 1 if limited, 0 if allowed
        res = await r.eval(LUA_RATE_LIMIT, 1, key, time.time(), window_secs, limit, secrets.token_hex(4))
        return res == 1
    except Exception as e:
        logging.error(f"Atomic rate limit failed for {key}: {e}")
        return False

def _is_admin_email(email: str | None) -> bool:
    if not email: return False
    return email.lower() in ADMIN_EMAILS

def _log_event(event: str, **fields):
    payload = {"event": event, **fields}
    logging.info(json.dumps(payload, default=str, sort_keys=True))

def _hash_key(api_key: str, salt: str) -> str:
    # Use PBKDF2 for a more robust (but still fast enough) hash than plain SHA256
    key = hashlib.pbkdf2_hmac("sha256", api_key.encode("utf-8"), salt.encode("utf-8"), 10000)
    return key.hex()

def _key_metadata(raw_key: str) -> dict:
    salt = secrets.token_hex(16)
    return {
        "key_hash": _hash_key(raw_key, salt),
        "salt": salt,
        "key_prefix": raw_key[:7],
        "key_suffix": raw_key[-4:],
    }

def _key_preview(prefix: str | None, suffix: str | None) -> str:
    if prefix and suffix:
        return f"{prefix}...{suffix}"
    return "unknown"

def _resolve_risk_config(key_data: dict) -> dict:
    config = dict(RISK_CONFIG)
    for name in RISK_CONFIG:
        val = key_data.get(f"risk_{name}")
        if val is not None:
            try:
                coerced = RISK_CONFIG_TYPES[name](val)
                # Strict Bound Checking
                if name in RISK_CONFIG_BOUNDS:
                    low, high = RISK_CONFIG_BOUNDS[name]
                    coerced = max(low, min(high, coerced))
                config[name] = coerced
            except (ValueError, TypeError):
                pass
    return config

def _has_custom_risk_profile(key_data: dict) -> bool:
    for name in RISK_CONFIG:
        if f"risk_{name}" in key_data:
            return True
    return False

def _coerce_risk_value(name: str, value: Any) -> Any:
    expected_type = RISK_CONFIG_TYPES.get(name)
    if not expected_type: return value
    try:
        return expected_type(value)
    except (ValueError, TypeError):
        return value

def _validate_risk_value(name: str, value: Any) -> Any:
    if name not in RISK_CONFIG_BOUNDS: return value
    low, high = RISK_CONFIG_BOUNDS[name]
    if value < low or value > high:
        raise HTTPException(status_code=400, detail=f"{name} must be between {low} and {high}")
    return value

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

async def _log_risk_profile_change(email: str, actor: str, action: str, previous_config: dict, new_config: dict):
    try:
        audit_id = secrets.token_hex(12)
        payload = {
            "audit_id": audit_id,
            "email": email,
            "actor": actor,
            "action": action,
            "previous_config": json.dumps(previous_config),
            "new_config": json.dumps(new_config),
            "timestamp": time.time(),
        }
        await AUDIT_STORE.insert_risk_profile_audit(payload)
    except Exception as e:
        logging.error(f"Risk profile audit failed: {e}")
