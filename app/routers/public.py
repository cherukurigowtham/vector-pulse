import time
import secrets
import logging
import hashlib
from fastapi import APIRouter, HTTPException, Request, Response
from app.models import PublicRegisterRequest, PilotRequest, RegisterRequest, AuthRequest
from app.core.redis import r
from app.core.helpers import (
    _log_event, _key_metadata, _is_admin_email, 
    _sliding_window_rate_limit
)
from app.core.security import ADMIN_KEY, _hash_password, _create_session
from app.core.config import RATE_LIMITS

router = APIRouter(tags=["public"])

@router.post("/auth/signup", summary="Create a new user account")
async def signup(req: AuthRequest, response: Response, request: Request):
    client_ip = getattr(request.client, "host", "unknown")
    if await _sliding_window_rate_limit(f"ratelimit:signup:{client_ip}", 5, 60):
        # 5 signups per minute per IP
        raise HTTPException(status_code=429, detail="Too many signup attempts. Please try again later.")

    if _is_admin_email(req.email):
        raise HTTPException(status_code=403, detail="Sovereign Identity Reserved")

    if await r.hexists(f"user:{req.email}", "pwd_hash"):
        raise HTTPException(status_code=400, detail="Email already registered")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(req.password, salt)
    
    raw_key = f"vp_live_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    # Important: We use sha256 for the lookup key (for fast indexing), 
    # but store the salted PBKDF2 hash inside for verification.
    legacy_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    async with r.pipeline() as pipe:
        pipe.hset(f"user:{req.email}", mapping={
            "pwd_hash": pwd_hash,
            "salt": salt,
            "key_hash": legacy_hash, # Lookup hint
            "key_prefix": key_meta["key_prefix"],
            "key_suffix": key_meta["key_suffix"],
            "plan": "free",
        })
        pipe.hset(f"apikey:{legacy_hash}", mapping={
            "email": req.email,
            "plan": "free",
            "key_hash": key_meta["key_hash"], # Salted PBKDF2
            "salt": key_meta["salt"],
            "key_prefix": key_meta["key_prefix"],
            "key_suffix": key_meta["key_suffix"],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        pipe.sadd("admin:all_keys", legacy_hash)
        pipe.set(f"emailkey:{req.email}", legacy_hash)
        await pipe.execute()
    
    await _create_session(req.email, response, request)
    return {"message": "Account created successfully", "api_key": raw_key}

@router.post("/auth/login", summary="Log in to an existing account")
async def login(req: AuthRequest, response: Response, request: Request):
    client_ip = getattr(request.client, "host", "unknown")
    if await _sliding_window_rate_limit(f"ratelimit:login:{client_ip}", 5, 60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

    user_data = await r.hgetall(f"user:{req.email}")
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    pwd_hash = _hash_password(req.password, user_data["salt"])
    if pwd_hash != user_data["pwd_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    await _create_session(req.email, response, request)
    return {"message": "Logged in successfully"}

@router.post("/auth/logout", summary="End the current session")
async def logout(request: Request, response: Response):
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

@router.post("/pilot-request", summary="Submit a pilot request from the landing page")
async def request_pilot(req: PilotRequest, request: Request):
    normalized_email = req.email.strip().lower()
    key = f"pilot_request:{normalized_email}"
    
    payload = {
        "name": req.name.strip(),
        "email": normalized_email,
        "company": req.company.strip(),
        "category": req.category,
        "monthly_orders": req.monthly_orders,
        "cod_share": req.cod_share,
        "status": "new",
        "submitted_at": str(time.time()),
        "ip": getattr(request.client, "host", "unknown")
    }
    
    await r.hset(key, mapping=payload)
    await r.sadd("pilot_request_emails", normalized_email)
    _log_event("pilot_request_created", email=normalized_email, company=req.company)
    return {"status": "success", "message": "Pilot request received. Our team will contact you soon."}

@router.post("/v1/register", summary="Register for an API key")
async def register(req: RegisterRequest, request: Request):
    client_ip = getattr(request.client, "host", "unknown")
    if await _sliding_window_rate_limit(f"ratelimit:register:{client_ip}", 2, 86400):
        # Max 2 registrations per day per IP
        raise HTTPException(status_code=429, detail="Too many registration requests. Please contact support.")

    if req.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    if req.plan not in RATE_LIMITS:
        raise HTTPException(status_code=400, detail=f"Plan must be one of: {list(RATE_LIMITS)}")

    raw_key = f"vp_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    legacy_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    async with r.pipeline() as pipe:
        pipe.hset(
            f"apikey:{legacy_hash}",
            mapping={
                "email": req.email,
                "plan": req.plan,
                "key_hash": key_meta["key_hash"],
                "salt": key_meta["salt"],
                "key_prefix": key_meta["key_prefix"],
                "key_suffix": key_meta["key_suffix"],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        pipe.sadd("admin:all_keys", legacy_hash)
        pipe.set(f"emailkey:{req.email}", legacy_hash)
        await pipe.execute()

    return {
        "api_key": raw_key,
        "plan": req.plan,
        "monthly_limit": RATE_LIMITS[req.plan],
        "note": "Store this key safely. It will not be shown again.",
    }

@router.post("/v1/public/request-free-key", summary="Issue a free tier API key instantly")
async def request_free_key(req: PublicRegisterRequest, request: Request):
    client_ip = getattr(request.client, "host", "unknown")
    
    if await r.get(f"ratelimit:ip:{client_ip}"):
         raise HTTPException(status_code=429, detail="Only one free key allowed per day per IP.")

    if await _sliding_window_rate_limit(f"ratelimit:free_key:{client_ip}", 1, 86400):
         raise HTTPException(status_code=429, detail="Only one free key allowed per day per IP.")

    raw_key = f"vp_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    legacy_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    async with r.pipeline() as pipe:
        pipe.setex(f"ratelimit:ip:{client_ip}", 86400, "1")
        pipe.hset(
            f"apikey:{legacy_hash}",
            mapping={
                "email": req.email,
                "plan": "free",
                "key_hash": key_meta["key_hash"],
                "salt": key_meta["salt"],
                "key_prefix": key_meta["key_prefix"],
                "key_suffix": key_meta["key_suffix"],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        pipe.sadd("admin:all_keys", legacy_hash)
        pipe.set(f"emailkey:{req.email}", legacy_hash)
        await pipe.execute()

    return {
        "api_key": raw_key,
        "plan": "free",
        "monthly_limit": RATE_LIMITS["free"],
        "note": "Free key generated. Valid for 1000 orders/month."
    }
