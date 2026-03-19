import secrets
import time
import hashlib
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from pydantic import BaseModel
from app.core.security import create_jwt_token, _hash_password, require_role, require_admin
from app.repositories.factory import get_merchant_repo
from app.repositories.merchant_repository import MerchantRepository
from app.core.redis import r, rk
from app.db.database import AUDIT_STORE
from app.models.schemas import (
    AuthRequest, ForgotPasswordRequest, ResetPasswordRequest
)
from app.core.helpers import (
    _sliding_window_rate_limit, _is_admin_email, 
    _key_metadata, _is_disposable_email, _log_event
)

router = APIRouter(prefix="/security/auth", tags=["Security Auth"])

class KeyCreateRequest(BaseModel):
    name: Optional[str] = "Default Key"

class KeyResponse(BaseModel):
    key_prefix: str
    key_suffix: str
    created_at: str
    role: str
    key_hash: str # This is the unique identifier (legacy hash)

@router.post("/signup", summary="Create a new user account")
async def signup(req: AuthRequest, response: Response, request: Request, repo: MerchantRepository = Depends(get_merchant_repo)):
    client_ip = getattr(request.client, "host", "unknown")
    if await _sliding_window_rate_limit(rk(f"ratelimit:signup:{client_ip}"), 5, 60):
        raise HTTPException(status_code=429, detail="Too many signup attempts.")

    # Prevent creation of the primary admin via public signup
    if _is_admin_email(req.email):
        raise HTTPException(status_code=403, detail="Sovereign Identity Reserved")

    if _is_disposable_email(req.email):
        raise HTTPException(status_code=400, detail="Enterprise security policy: Disposable email addresses are not permitted.")

    # Strict check: Require basic business details
    if not req.full_name or not req.company_name:
         raise HTTPException(status_code=400, detail="Full name and company name are mandatory for merchant identity verification.")

    if await r.hexists(rk(f"user:{req.email}"), "pwd_hash") or await r.hexists(rk(f"user:{req.email}"), "password_hash"):
        raise HTTPException(status_code=400, detail="Email already registered")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(req.password, salt)
    
    raw_key = f"vp_live_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    legacy_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    team_id = secrets.token_hex(8)
    # Create team in Postgres
    await AUDIT_STORE.create_team(team_id, req.company_name or f"{req.email}'s Team", req.email)

    async with r.pipeline() as pipe:
        pipe.hset(rk(f"user:{req.email}"), mapping={
            "pwd_hash": pwd_hash,
            "salt": salt,
            "key_hash": legacy_hash,
            "key_prefix": key_meta["key_prefix"],
            "key_suffix": key_meta["key_suffix"],
            "plan": "free",
            "role": "ADMIN",
            "team_id": team_id,
            "full_name": req.full_name,
            "company_name": req.company_name,
            "merchant_category": req.merchant_category or "retail",
            "expected_volume": req.expected_monthly_volume or "0-100",
            "onboarded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        pipe.hset(rk(f"apikey:{legacy_hash}"), mapping={
            "email": req.email,
            "plan": "free",
            "key_hash": key_meta["key_hash"],
            "salt": key_meta["salt"],
            "key_prefix": key_meta["key_prefix"],
            "key_suffix": key_meta["key_suffix"],
            "role": "ADMIN",
            "team_id": team_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        pipe.sadd(rk("admin:all_keys"), legacy_hash)
        pipe.set(rk(f"emailkey:{req.email}"), legacy_hash)
        await pipe.execute()
    
    # Generate JWT token
    token = create_jwt_token({"sub": req.email, "role": "ADMIN", "team_id": team_id})
    response.set_cookie(key="vp_token", value=token, httponly=True)
    return {"message": "Account created successfully", "api_key": raw_key}

@router.post("/login", summary="Merchant Login.")
async def login(req: AuthRequest, response: Response, request: Request, repo: MerchantRepository = Depends(get_merchant_repo)):
    client_ip = getattr(request.client, "host", "unknown")
    if await _sliding_window_rate_limit(f"ratelimit:login:{client_ip}", 10, 60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
        
    user = await repo.get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password if hash exists (checking both legacy password_hash and pwd_hash)
    if "pwd_hash" in user and "salt" in user:
        provided_hash = _hash_password(req.password, user["salt"])
        if provided_hash != user["pwd_hash"]:
             raise HTTPException(status_code=401, detail="Invalid credentials")
    elif "password_hash" in user and "salt" in user:
        provided_hash = _hash_password(req.password, user["salt"])
        if provided_hash != user["password_hash"]:
             raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT token
    role = user.get("role", "VIEWER")
    team_id = user.get("team_id", "personal")
    token = create_jwt_token({"sub": req.email, "role": role, "team_id": team_id})
    response.set_cookie(key="vp_token", value=token, httponly=True)
    return {"status": "success", "message": "Logged in successfully"}

@router.post("/forgot-password", summary="Initiate password recovery")
async def forgot_password(req: ForgotPasswordRequest, request: Request):
    client_ip = getattr(request.client, "host", "unknown")
    if await _sliding_window_rate_limit(rk(f"ratelimit:forgot_pwd:{client_ip}"), 3, 3600):
        raise HTTPException(status_code=429, detail="Check again in an hour.")

    if not await r.hexists(rk(f"user:{req.email}"), "pwd_hash"):
        return {"message": "If registered, check your email."}

    reset_token = secrets.token_urlsafe(32)
    await r.setex(rk(f"pwd_reset:{reset_token}"), 3600, req.email)
    return {"message": "If registered, check your email.", "debug_token": reset_token}

@router.post("/reset-password", summary="Complete password recovery")
async def reset_password(req: ResetPasswordRequest):
    email = await r.get(rk(f"pwd_reset:{req.token}"))
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(req.new_password, salt)
    
    async with r.pipeline() as pipe:
        pipe.hset(rk(f"user:{email}"), mapping={"pwd_hash": pwd_hash, "salt": salt})
        pipe.delete(rk(f"pwd_reset:{req.token}"))
        await pipe.execute()
        
    _log_event("password_reset_complete", email=email)
    return {"message": "Password updated successfully."}

@router.get("/me", summary="Check current auth state.")
async def get_me(request: Request):
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user

@router.post("/logout", summary="End the current session")
async def logout(response: Response):
    response.delete_cookie("vp_token")
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/keys", summary="List all API keys for the current team")
async def list_keys(user: dict = Depends(require_role(["ADMIN", "ANALYST"]))):
    team_id = user.get("team_id")
    if not team_id:
        raise HTTPException(status_code=400, detail="User not associated with a team")
    
    # In a real app, we'd have a secondary index `team_keys:{team_id}`
    # For now, we search `admin:all_keys` (which contains ALL global keys)
    # This is inefficient but fits the current schema.
    all_keys = await r.smembers(rk("admin:all_keys"))
    team_keys = []
    for kh in all_keys:
        profile = await r.hgetall(rk(f"apikey:{kh}"))
        if profile.get("team_id") == team_id:
            team_keys.append({
                "key_prefix": profile.get("key_prefix", "unknown"),
                "key_suffix": profile.get("key_suffix", "unknown"),
                "created_at": profile.get("created_at", "unknown"),
                "role": profile.get("role", "ADMIN"),
                "key_hash": kh
            })
    return team_keys

@router.post("/keys", summary="Create a new API key")
async def create_key(req: KeyCreateRequest, user: dict = Depends(require_role(["ADMIN"]))):
    email = user.get("email")
    team_id = user.get("team_id")
    
    raw_key = f"vp_live_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    legacy_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    async with r.pipeline() as pipe:
        pipe.hset(rk(f"apikey:{legacy_hash}"), mapping={
            "email": email,
            "name": req.name,
            "key_hash": key_meta["key_hash"],
            "salt": key_meta["salt"],
            "key_prefix": key_meta["key_prefix"],
            "key_suffix": key_meta["key_suffix"],
            "role": "ADMIN",
            "team_id": team_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        pipe.sadd(rk("admin:all_keys"), legacy_hash)
        await pipe.execute()
    
    return {"api_key": raw_key, "key_hash": legacy_hash}

@router.delete("/keys/{key_hash}", summary="Revoke an API key")
async def revoke_key(key_hash: str, user: dict = Depends(require_role(["ADMIN"]))):
    team_id = user.get("team_id")
    
    profile = await r.hgetall(rk(f"apikey:{key_hash}"))
    if not profile:
        raise HTTPException(status_code=404, detail="Key not found")
    
    if profile.get("team_id") != team_id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this key")
    
    async with r.pipeline() as pipe:
        pipe.delete(rk(f"apikey:{key_hash}"))
        pipe.srem(rk("admin:all_keys"), key_hash)
        # Also remove from emailkey index if it's the primary one
        email = profile.get("email")
        if email:
            current_primary = await r.get(rk(f"emailkey:{email}"))
            if current_primary == key_hash:
                pipe.delete(rk(f"emailkey:{email}"))
        await pipe.execute()
    
    return {"status": "success", "message": "Key revoked"}
