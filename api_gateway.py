from fastapi import FastAPI, HTTPException, Security, Depends, Request, Header, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import vector_pulse
import os
import time
import logging
import secrets
import hashlib

# ── Logging setup ──────────────────────────────────────────────────────────────
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

app = FastAPI(
    title="Vector-Pulse RTO Shield API",
    description="Real-time fraud detection for Indian e-commerce. Stop RTO losses instantly.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Redis Feature Store ────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=0,
    decode_responses=True,
    ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
)

# ── Constants ──────────────────────────────────────────────────────────────────
HISTORY_LEN = 10
Z_SCORE_THRESHOLD = 3.0
VELOCITY_WINDOW_SECS = 5
VELOCITY_MAX_ORDERS = 3
SYBIL_ADDRESS_LIMIT = 3

RATE_LIMITS = {
    "free": 1_000,
    "starter": 10_000,
    "growth": 100_000,
    "scale": 1_000_000,
}

# ── API Key Auth ───────────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "vp_admin_changeme")


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def require_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    key_hash = _hash_key(api_key)
    key_data = r.hgetall(f"apikey:{key_hash}")

    if not key_data:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Rate limiting: rolling monthly counter
    month_key = f"usage:{key_hash}:{time.strftime('%Y-%m')}"
    usage = int(r.get(month_key) or 0)
    plan = key_data.get("plan", "starter")
    limit = RATE_LIMITS.get(plan, RATE_LIMITS["starter"])

    if usage >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit of {limit:,} calls reached for {plan} plan. Upgrade at vectorpulse.vercel.app",
        )

    r.incr(month_key)
    r.expire(month_key, 60 * 60 * 24 * 35)  # 35 days TTL
    return key_data


# ── Request Models ─────────────────────────────────────────────────────────────
class Order(BaseModel):
    uid: str
    amt: float
    addr: str
    pin: str


class RegisterRequest(BaseModel):
    email: str
    plan: str = "starter"
    admin_key: str

class PublicRegisterRequest(BaseModel):
    email: str

class AuthRequest(BaseModel):
    email: str
    password: str


# ── Fraud Detection Helpers ────────────────────────────────────────────────────
def _check_velocity(uid: str) -> bool:
    now = time.time()
    window_start = now - VELOCITY_WINDOW_SECS
    vel_key = f"velocity:{uid}"
    r.zadd(vel_key, {str(now): now})
    r.zremrangebyscore(vel_key, 0, window_start)
    r.expire(vel_key, VELOCITY_WINDOW_SECS * 2)
    return r.zcard(vel_key) > VELOCITY_MAX_ORDERS


def _check_sybil(uid: str, address: str) -> bool:
    address_hash = hash(address.strip().lower())
    key = f"addr:{address_hash}"
    r.sadd(key, uid)
    return r.scard(key) > SYBIL_ADDRESS_LIMIT


def _check_price_anomaly(uid: str, amount: float) -> tuple[bool, float, float]:
    history_key = f"history:{uid}"
    history = [float(x) for x in r.lrange(history_key, 0, HISTORY_LEN - 1)]
    avg, std_dev = vector_pulse.calculate_stats(history)
    is_anomaly = len(history) >= 2 and vector_pulse.is_anomaly_sigma(
        amount, avg, std_dev, Z_SCORE_THRESHOLD
    )
    r.lpush(history_key, amount)
    r.ltrim(history_key, 0, HISTORY_LEN - 1)
    return is_anomaly, avg, std_dev


def _get_trust_score(uid: str) -> float:
    delivered = int(r.get(f"rep:{uid}:delivered") or 0)
    total = int(r.get(f"rep:{uid}:total") or 0)
    return vector_pulse.calculate_trust_score(delivered, total)


# ── Public Endpoints ───────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("landing/index.html")

@app.get("/admin", include_in_schema=False)
async def admin_portal():
    return FileResponse("landing/admin.html")


@app.get("/health")
async def health():
    try:
        r.ping()
        return {"status": "ok", "redis": "connected"}
    except Exception:
        return {"status": "degraded", "redis": "unreachable"}


# ── Admin: Issue API Keys  ─────────────────────────────────────────────────────
def require_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return x_admin_key

@app.get("/v1/admin/users", summary="List all registered API keys and their usage")
async def get_all_users(_: str = Depends(require_admin)):
    keys = r.smembers("admin:all_keys")
    users = []
    
    current_month = time.strftime('%Y-%m')
    for key_hash in keys:
        key_data = r.hgetall(f"apikey:{key_hash}")
        if not key_data:
            continue
            
        usage = int(r.get(f"usage:{key_hash}:{current_month}") or 0)
        
        users.append({
            "email": key_data.get("email", "unknown"),
            "plan": key_data.get("plan", "unknown"),
            "created_at": key_data.get("created_at", "unknown"),
            "usage_this_month": usage,
            "limit": RATE_LIMITS.get(key_data.get("plan", "free"), 1_000)
        })
        
    users.sort(key=lambda x: x["usage_this_month"], reverse=True)
    return {"users": users, "total_users": len(keys)}

@app.post("/v1/register", summary="Issue an API key (admin only)")
async def register(req: RegisterRequest):
    if req.admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    if req.plan not in RATE_LIMITS:
        raise HTTPException(status_code=400, detail=f"Plan must be one of: {list(RATE_LIMITS)}")

    raw_key = f"vp_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)

    r.hset(
        f"apikey:{key_hash}",
        mapping={
            "email": req.email,
            "plan": req.plan,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    r.sadd("admin:all_keys", key_hash)

    return {
        "api_key": raw_key,
        "plan": req.plan,
        "monthly_limit": RATE_LIMITS[req.plan],
        "note": "Store this key safely. It will not be shown again.",
    }

@app.post("/v1/public/request-free-key", summary="Issue a free tier API key instantly")
async def request_free_key(req: PublicRegisterRequest, request: Request):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()
    
    if r.get(f"ratelimit:ip:{client_ip}"):
         raise HTTPException(status_code=429, detail="Only one free key allowed per day per IP.")
         
    r.setex(f"ratelimit:ip:{client_ip}", 86400, "1")
    
    raw_key = f"vp_test_{secrets.token_urlsafe(24)}"
    key_hash = _hash_key(raw_key)

    r.hset(
        f"apikey:{key_hash}",
        mapping={
            "email": req.email,
            "plan": "free",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    r.sadd("admin:all_keys", key_hash)

    return {
        "api_key": raw_key,
        "plan": "free",
        "monthly_limit": RATE_LIMITS["free"],
        "note": "Store this test key safely. It will not be shown again."
    }

# ── User Auth (B2C) ────────────────────────────────────────────────────────────
def _hash_password(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return key.hex()

@app.post("/v1/auth/signup", summary="Create a new user account")
async def auth_signup(req: AuthRequest, response: Response, request: Request):
    if r.hexists(f"user:{req.email}", "pwd_hash"):
        raise HTTPException(status_code=400, detail="Email already registered")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(req.password, salt)
    
    # Generate API key
    raw_key = f"vp_live_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)

    # Store User
    r.hset(f"user:{req.email}", mapping={
        "pwd_hash": pwd_hash,
        "salt": salt,
        "api_key": raw_key
    })

    # Store API Key Profile
    r.hset(f"apikey:{key_hash}", mapping={
        "email": req.email,
        "plan": "free",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    r.sadd("admin:all_keys", key_hash)

    # Create Session Cookie
    session_id = secrets.token_urlsafe(64)
    r.setex(f"session:{session_id}", 86400 * 30, req.email) # 30 days
    
    # Secure HTTPOnly Cookie
    is_https = "https" in str(request.url)
    response.set_cookie(key="vp_session", value=session_id, httponly=True, secure=is_https, samesite="lax", max_age=86400*30)
    
    return {"message": "Account created successfully"}

@app.post("/v1/auth/login", summary="Log in to an existing account")
async def auth_login(req: AuthRequest, response: Response, request: Request):
    user_data = r.hgetall(f"user:{req.email}")
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    pwd_hash = _hash_password(req.password, user_data["salt"])
    if pwd_hash != user_data["pwd_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Create Session Cookie
    session_id = secrets.token_urlsafe(64)
    r.setex(f"session:{session_id}", 86400 * 30, req.email)
    
    is_https = "https" in str(request.url)
    response.set_cookie(key="vp_session", value=session_id, httponly=True, secure=is_https, samesite="lax", max_age=86400*30)
    
    return {"message": "Logged in successfully"}

@app.post("/v1/auth/logout", summary="End the current session")
async def auth_logout(request: Request, response: Response):
    session_id = request.cookies.get("vp_session")
    if session_id:
        r.delete(f"session:{session_id}")
    response.delete_cookie("vp_session")
    return {"message": "Logged out successfully"}

@app.get("/v1/auth/me", summary="Get the current logged in user's profile and API key")
async def auth_me(request: Request):
    session_id = request.cookies.get("vp_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    email = r.get(f"session:{session_id}")
    if not email:
        raise HTTPException(status_code=401, detail="Session expired")
        
    user_data = r.hgetall(f"user:{email}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
        
    # We never return passwords or salts. Just the key and email.
    return {
        "email": email,
        "api_key": user_data.get("api_key")
    }

# ── Core: Risk Check ───────────────────────────────────────────────────────────
@app.post("/v1/risk-check", summary="Evaluate an order for fraud risk")
async def check_order(order: Order, key_data: dict = Depends(require_api_key)):
    start_time = time.perf_counter()
    uid, amount, address = order.uid, order.amt, order.addr
    reasons = []

    if _check_velocity(uid):
        reasons.append("HIGH_VELOCITY")
        r.incr("stat:velocity")
        logging.warning(f"USER: {uid} | AMT: {amount} | FLAG: VELOCITY")

    if _check_sybil(uid, address):
        reasons.append("ADDRESS_SYBIL_DETECTED")
        r.incr("stat:sybil")
        logging.warning(f"USER: {uid} | ADDR: {address} | FLAG: SYBIL")

    is_price_anomaly, avg, std_dev = _check_price_anomaly(uid, amount)
    if is_price_anomaly:
        reasons.append("HIGH_DEVIATION")
        r.incr("stat:price")
        logging.warning(f"USER: {uid} | AMT: ₹{amount:.2f} | AVG: ₹{avg:.2f} | FLAG: HIGH_DEVIATION")

    trust_score = _get_trust_score(uid)
    if trust_score < 30.0 and trust_score != 50.0:
        reasons.append("LOW_TRUST_SCORE")

    is_risky = len(reasons) > 0
    action = "FORCE_PREPAID" if is_risky else "ALLOW_COD"

    if is_risky:
        r.incrby("total_savings_inr", 70)
        r.lpush("recent_blocks", f"{uid}: {', '.join(reasons)}")
        r.ltrim("recent_blocks", 0, 49)

    r.incr(f"rep:{uid}:total")

    latency = (time.perf_counter() - start_time) * 1000
    return {
        "uid": uid,
        "decision": action,
        "risk_factors": reasons,
        "trust_score": round(trust_score, 1),
        "avg_order_amt": round(avg, 2),
        "latency_ms": f"{latency:.2f}ms",
    }


# ── Reputation Feedback ────────────────────────────────────────────────────────
@app.post("/v1/order-delivered", summary="Mark order as delivered — builds user trust")
async def mark_delivered(uid: str, key_data: dict = Depends(require_api_key)):
    r.incr(f"rep:{uid}:delivered")
    r.incr(f"rep:{uid}:total")
    return {"uid": uid, "trust_score": round(_get_trust_score(uid), 1), "status": "updated"}
