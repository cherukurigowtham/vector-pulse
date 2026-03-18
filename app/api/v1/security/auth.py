import secrets
import time
import hashlib
from fastapi import APIRouter, Depends, Response, Request, HTTPException
from pydantic import BaseModel
from app.core.security import create_jwt_token, _hash_password
from app.repositories.factory import get_merchant_repo
from app.repositories.merchant_repository import MerchantRepository
from app.core.redis import r
from app.db.database import AUDIT_STORE
from app.core.helpers import _sliding_window_rate_limit, _is_admin_email, _key_metadata

router = APIRouter(prefix="/security/auth", tags=["Security Auth"])

class AuthRequest(BaseModel):
    email: str
    password: str

@router.post("/signup", summary="Create a new user account")
async def signup(req: AuthRequest, response: Response, request: Request, repo: MerchantRepository = Depends(get_merchant_repo)):
    client_ip = getattr(request.client, "host", "unknown")
    if await _sliding_window_rate_limit(f"ratelimit:signup:{client_ip}", 5, 60):
        raise HTTPException(status_code=429, detail="Too many signup attempts.")

    # Prevent creation of the primary admin via public signup
    if _is_admin_email(req.email):
        raise HTTPException(status_code=403, detail="Sovereign Identity Reserved")

    if await r.hexists(f"user:{req.email}", "pwd_hash") or await r.hexists(f"user:{req.email}", "password_hash"):
        raise HTTPException(status_code=400, detail="Email already registered")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(req.password, salt)
    
    raw_key = f"vp_live_{secrets.token_urlsafe(32)}"
    key_meta = _key_metadata(raw_key)
    legacy_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    team_id = secrets.token_hex(8)
    # Create team in Postgres
    await AUDIT_STORE.create_team(team_id, f"{req.email}'s Team", req.email)

    async with r.pipeline() as pipe:
        pipe.hset(f"user:{req.email}", mapping={
            "pwd_hash": pwd_hash,
            "salt": salt,
            "key_hash": legacy_hash,
            "key_prefix": key_meta["key_prefix"],
            "key_suffix": key_meta["key_suffix"],
            "plan": "free",
            "role": "ADMIN",
            "team_id": team_id
        })
        pipe.hset(f"apikey:{legacy_hash}", mapping={
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
        pipe.sadd("admin:all_keys", legacy_hash)
        pipe.set(f"emailkey:{req.email}", legacy_hash)
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

@router.get("/me", summary="Check current auth state.")
async def get_me(request: Request):
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user

@router.post("/logout", summary="End the current session")
async def logout(response: Response):
    response.delete_cookie("vp_token")
    return {"status": "success", "message": "Logged out successfully"}
