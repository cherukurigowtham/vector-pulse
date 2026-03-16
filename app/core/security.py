import secrets
import hashlib
from fastapi import Request, Response, HTTPException, Security, Depends, Header
from fastapi.security import APIKeyHeader
from app.core.redis import r
from app.core.helpers import (
    ADMIN_KEY, PRIMARY_ADMIN_EMAIL, SESSION_COOKIE_SECURE, 
    _is_admin_email, _hash_key, _log_event
)
import logging

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

def _hash_password(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return key.hex()

async def _create_session(email: str, response: Response, request: Request) -> None:
    session_id = secrets.token_urlsafe(64)
    csrf_token = secrets.token_urlsafe(64)
    
    async with r.pipeline() as pipe:
        pipe.setex(f"session:{session_id}", 86400 * 30, email)
        pipe.setex(f"csrf:{session_id}", 86400 * 30, csrf_token)
        pipe.sadd(f"session_index:{email}", session_id)
        await pipe.execute()

    response.set_cookie(
        key="vp_session",
        value=session_id,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        max_age=86400 * 30,
    )
    # Double-submit cookie pattern: provide CSRF token in a non-httponly cookie
    response.set_cookie(
        key="vp_csrf",
        value=csrf_token,
        httponly=False,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        max_age=86400 * 30,
    )

async def require_csrf(request: Request):
    """Enforce CSRF protection for state-changing cookie-based requests."""
    session_id = request.cookies.get("vp_session")
    if not session_id:
        return # Not using cookie auth
        
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return
        
    stored_csrf = await r.get(f"csrf:{session_id}")
    provided_csrf = request.headers.get("X-CSRF-Token")
    
    if not stored_csrf or provided_csrf != stored_csrf:
        logging.warning(f"CSRF validation failed for session {session_id[:8]}...")
        raise HTTPException(status_code=403, detail="CSRF token validation failed")

async def require_admin(request: Request, x_admin_header: str = Security(admin_key_header), _csrf = Depends(require_csrf)):
    if x_admin_header and x_admin_header == ADMIN_KEY:
        return PRIMARY_ADMIN_EMAIL
        
    session_id = request.cookies.get("vp_session")
    if session_id:
        email = await r.get(f"session:{session_id}")
        if _is_admin_email(email):
            return email
            
    raise HTTPException(status_code=403, detail="Invalid admin credentials or session")

async def require_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    
    # We need to find the profile first to get the salt.
    # We'll use the prefix as a hint to avoid checking every key if possible,
    # but since we store by hash, we need another way if we want to be efficient.
    # For now, we'll keep the key as the hash, but we'll need a "lookup" or a way to get the salt.
    # BEST PRACTICE: Store as `apikey:{prefix}` if prefix is long enough and unique, or use a lookup.
    # Our keys are `vp_live_{32 bytes}`, prefix is `vp_live`. That's not unique.
    
    # REVISED STRATEGY: 
    # 1. We'll store a mapping of `prefix:suffix` to `salt` and `key_hash` if possible, 
    #    but that's complex.
    # 2. For now, since we already have `emailkey:{email}`, we can use that for known emails.
    # 3. For general API keys, let's update the registration to store by a NEW unique identifier 
    #    or just use the hash of the key AS-IS but store the salt INSIDE the hash field (hash:salt).
    
    # Let's try the `hash_key` without salt first for legacy, then check salted.
    # Actually, let's just use the current key_hash (which is sha256) to FIND the record,
    # then if the record has a `salt` and a `salted_hash`, we verify it.
    
    legacy_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_data = await r.hgetall(f"apikey:{legacy_hash}")
    
    if not key_data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Check if it has a salt (meaning it's a NEW key)
    if "salt" in key_data:
        salt = key_data["salt"]
        expected_hash = key_data["key_hash"]
        actual_hash = _hash_key(api_key, salt)
        if actual_hash != expected_hash:
            raise HTTPException(status_code=403, detail="Invalid API key (Salt Match Fail)")
    
    return {"key_hash": legacy_hash, "data": key_data, "email": key_data.get("email")}

async def require_api_key_or_admin(
    request: Request,
    api_key: str = Security(api_key_header),
    x_admin_key: str = Header(None),
):
    if api_key:
        return await require_api_key(api_key)
    return await require_admin(request, x_admin_key)
