import jwt
import datetime
from fastapi import Request, Response, HTTPException, Security, Depends, Header
from fastapi.security import APIKeyHeader
from app.core.redis import r, rk
from app.core.config import (
    ADMIN_KEY, SESSION_COOKIE_SECURE, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
)
from app.core.helpers import (
    PRIMARY_ADMIN_EMAIL,
    _is_admin_email, _hash_key, _log_event
)
import logging

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

import secrets
import hashlib

def _hash_password(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return key.hex()

def create_jwt_token(data: dict) -> str:
    """Generates a professional JWT token for merchant auth."""
    payload = data.copy()
    if "exp" not in payload:
        payload["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def _create_session(email: str, response: Response, request: Request) -> None:
    session_id = secrets.token_urlsafe(64)
    csrf_token = secrets.token_urlsafe(64)
    
    # Fetch user role and team from database
    from app.db.database import AUDIT_STORE
    user_info = await AUDIT_STORE.get_user_role_and_team(email)
    role = user_info["role"] if user_info else "VIEWER"
    team_id = user_info["team_id"] if user_info else "personal"

    # Create JWT
    payload = {
        "sub": email,
        "role": role,
        "team_id": team_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    async with r.pipeline() as pipe:
        pipe.hset(rk(f"session:{session_id}"), mapping={
            "email": email,
            "role": role,
            "team_id": team_id,
            "jwt": token
        })
        pipe.expire(rk(f"session:{session_id}"), 86400 * 30)
        pipe.setex(rk(f"csrf:{session_id}"), 86400 * 30, csrf_token)
        pipe.sadd(rk(f"session_index:{email}"), session_id)
        await pipe.execute()

    response.set_cookie(
        key="vp_session",
        value=session_id,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        max_age=86400 * 30,
    )
    response.set_cookie(
        key="vp_token",
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        max_age=3600 * JWT_EXPIRATION_HOURS,
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

async def require_csrf(request: Request, x_csrf_token: str = Header(None), x_admin_key: str = Header(None)):
    """Validates the CSRF token from headers against the session's stored token."""
    # Bypass for Admin Key (DevOps/CI)
    if x_admin_key and x_admin_key == ADMIN_KEY:
        return
        
    session_id = request.cookies.get("vp_session")
    if not session_id:
        return # No session, let role/auth handler fail it

    # Only enforce for state-changing methods
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return

    stored_csrf = await r.get(rk(f"csrf:{session_id}"))
    provided_csrf = x_csrf_token
    
    if not stored_csrf or provided_csrf != stored_csrf:
        logging.warning(f"CSRF validation failed for session {session_id[:8]}...")
        raise HTTPException(status_code=403, detail="CSRF token validation failed")

def require_role(allowed_roles: list[str]):
    async def role_dependency(request: Request, x_admin_key: str = Header(None), _csrf = Depends(require_csrf)):
        # 1. Admin Key Bypass (Highest Priority for Automation)
        if x_admin_key and x_admin_key == ADMIN_KEY:
            return {"email": "automation@vantix.ai", "role": "ADMIN", "team_id": "system"}

        # 2. Middleware-injected user (JWT)
        user = getattr(request.state, "user", None)
        if user:
            role = user.get("role")
            if role in allowed_roles:
                return user
            logging.warning(f"Access denied for role {role}. Required: {allowed_roles}")
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # 3. Fallback to session check
        session_id = request.cookies.get("vp_session")
        if not session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session_data = await r.hgetall(rk(f"session:{session_id}"))
        if not session_data:
            raise HTTPException(status_code=401, detail="Session expired")
        
        role = session_data.get("role")
        if role not in allowed_roles:
            logging.warning(f"Access denied for role {role}. Required: {allowed_roles}")
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return session_data
    return role_dependency

async def require_admin(request: Request, x_admin_header: str = Security(admin_key_header), _csrf = Depends(require_csrf)):
    if x_admin_header and x_admin_header == ADMIN_KEY:
        return {"email": PRIMARY_ADMIN_EMAIL, "role": "ADMIN", "team_id": "system"}
    
    # Check middleware-injected user
    user = getattr(request.state, "user", None)
    if user and (user.get("role") == "ADMIN" or _is_admin_email(user.get("email"))):
        return user
        
    # Fallback to session check
    session_id = request.cookies.get("vp_session")
    if session_id:
        session_data = await r.hgetall(rk(f"session:{session_id}"))
        if session_data and (session_data.get("role") == "ADMIN" or _is_admin_email(session_data.get("email"))):
            return session_data
            
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
    key_data = await r.hgetall(rk(f"apikey:{legacy_hash}"))
    
    if not key_data:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Check if it has a salt (meaning it's a NEW key)
    if "salt" in key_data:
        salt = key_data["salt"]
        expected_hash = key_data["key_hash"]
        actual_hash = _hash_key(api_key, salt)
        if actual_hash != expected_hash:
            raise HTTPException(status_code=403, detail="Invalid API key (Salt Match Fail)")
    
    return {"key_hash": legacy_hash, "data": key_data, "email": key_data.get("email"), "team_id": key_data.get("team_id")}

def verify_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        return None

async def require_api_key_or_admin(
    request: Request,
    api_key: str = Security(api_key_header),
    x_admin_key: str = Header(None),
):
    if api_key:
        return await require_api_key(api_key)
    return await require_admin(request, x_admin_key)
