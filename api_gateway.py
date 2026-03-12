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
import httpx
import aiosqlite
import json
from geolite2 import geolite2

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

# ── Database Initialization ────────────────────────────────────────────────────
AUDIT_DB = "audit_log.db"

@app.on_event("startup")
async def startup_event():
    async with aiosqlite.connect(AUDIT_DB) as db:
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
        await db.commit()

# ── IP Intelligence Initialization ─────────────────────────────────────────────
GEO_READER = geolite2.reader()

# ── Redis Feature Store ────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

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


async def sliding_window_rate_limit(key_hash: str, limit: int) -> bool:
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
        return current_usage <= (limit / 1000) # Burst protection logic (e.g. 0.1% per minute)
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
        if not await sliding_window_rate_limit(key_hash, limit):
             raise HTTPException(status_code=429, detail="Too many requests in a short period (Burst Limit Reached)")

        async with r.pipeline() as pipe:
            pipe.incr(month_key)
            pipe.expire(month_key, 60 * 60 * 24 * 35)
            await pipe.execute()
            
        return key_data
    except Exception as e:
        if isinstance(e, HTTPException): raise
        logging.error(f"Redis Auth Error: {e}")
        raise HTTPException(status_code=500, detail="Identity service temporarily unavailable")


# ── Request Models ─────────────────────────────────────────────────────────────
class Order(BaseModel):
    uid: str
    amt: float
    addr: str
    pin: str
    ip: str = "127.0.0.1"
    shadow: bool = False # If True, will NOT block even if risky


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
# ── Internal Risk Modules (Optimised) ───────────────────────────────────────────
async def _check_velocity(uid: str) -> bool:
    try:
        now = time.time()
        window_start = now - VELOCITY_WINDOW_SECS
        vel_key = f"velocity:{uid}"
        async with r.pipeline() as pipe:
            pipe.zadd(vel_key, {str(now): now})
            pipe.zremrangebyscore(vel_key, 0, window_start)
            pipe.zcard(vel_key)
            pipe.expire(vel_key, VELOCITY_WINDOW_SECS * 2)
            res = await pipe.execute()
        return res[2] > VELOCITY_MAX_ORDERS
    except Exception as e:
        logging.error(f"Velocity Check Failed: {e}")
        return False # Safe fallback

async def _check_sybil(uid: str, address: str) -> bool:
    try:
        # Phase 12: Use Rust-based normalization for precision
        normalized = vector_pulse.normalize_address(address)
        # Use stable hash for consistency across restarts
        address_hash = hashlib.sha256(normalized.encode()).hexdigest()
        key = f"addr:{address_hash}"
        async with r.pipeline() as pipe:
            pipe.sadd(key, uid)
            pipe.scard(key)
            pipe.expire(key, 86400 * 7) # Keep for 7 days
            res = await pipe.execute()
        return res[1] > SYBIL_ADDRESS_LIMIT
    except Exception as e:
        logging.error(f"Sybil Check Failed: {e}")
        return False

async def _check_price_anomaly(uid: str, amount: float) -> tuple[bool, float, float]:
    try:
        history_key = f"history:{uid}"
        history_raw = await r.lrange(history_key, 0, HISTORY_LEN - 1)
        history = [float(x) for x in history_raw]
        
        avg, std_dev = vector_pulse.calculate_stats(history)
        is_anomaly = len(history) >= 2 and vector_pulse.is_anomaly_sigma(
            amount, avg, std_dev, Z_SCORE_THRESHOLD
        )
        
        async with r.pipeline() as pipe:
            pipe.lpush(history_key, amount)
            pipe.ltrim(history_key, 0, HISTORY_LEN - 1)
            pipe.expire(history_key, 60 * 60 * 24 * 7) # Week TTL
            await pipe.execute()
            
        return is_anomaly, avg, std_dev
    except Exception as e:
        logging.error(f"Price Anomaly Check Failed: {e}")
        return False, 0.0, 0.0

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
        
        # 2. Check cache for specialized VPN flags
        cache_key = f"ipint:{ip}"
        cached = await r.get(cache_key)
        if cached is not None:
            return cached == "1" or is_risky_geo

        # 3. Fallback to specialized VPN Intelligence
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}?fields=proxy,hosting", timeout=1.0)
            if resp.status_code == 200:
                data = resp.json()
                is_proxy = data.get("proxy", False) or data.get("hosting", False)
                
                # Cache results
                await r.setex(cache_key, 86400, "1" if is_proxy else "0")
                return is_proxy or is_risky_geo
                
        return is_risky_geo
    except Exception as e:
        logging.error(f"IP Intelligence Lookup Failed for {ip}: {e}")
        return False

async def _log_audit_event(risk_id: str, email: str, context: dict, decision: str, shadow: bool):
    try:
        async with aiosqlite.connect(AUDIT_DB) as db:
            await db.execute("""
                INSERT INTO risk_audit 
                (risk_id, uid, email, risk_score, decision, shadow_mode, reasons, metrics, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                risk_id, 
                context["uid"], 
                email, 
                context["score"], 
                decision, 
                1 if shadow else 0,
                ",".join(context["flags"]),
                json.dumps(context["metrics"]),
                context["timestamp"]
            ))
            await db.commit()
    except Exception as e:
        logging.error(f"Audit Logging Failed: {e}")

async def _get_trust_score(uid: str) -> float:
    try:
        async with r.pipeline() as pipe:
            pipe.get(f"rep:{uid}:delivered")
            pipe.get(f"rep:{uid}:total")
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
    return FileResponse("landing/admin.html")


@app.get("/health")
async def health():
    try:
        await r.ping()
        return {"status": "ok", "redis": "connected", "mode": "production"}
    except Exception:
        return {"status": "degraded", "redis": "unreachable", "mode": "safe_fallback"}


# ── Admin: Issue API Keys  ─────────────────────────────────────────────────────
def require_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return x_admin_key

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
                
            usage = int(res[1] or 0)
            
            users.append({
                "email": key_data.get("email", "unknown"),
                "plan": key_data.get("plan", "unknown"),
                "created_at": key_data.get("created_at", "unknown"),
                "usage_this_month": usage,
                "limit": RATE_LIMITS.get(key_data.get("plan", "free"), 1_000)
            })
        except: continue
        
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

    async with r.pipeline() as pipe:
        pipe.hset(
            f"apikey:{key_hash}",
            mapping={
                "email": req.email,
                "plan": req.plan,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        pipe.sadd("admin:all_keys", key_hash)
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
         
    async with r.pipeline() as pipe:
        pipe.setex(f"ratelimit:ip:{client_ip}", 86400, "1")
        pipe.hset(
            f"apikey:{key_hash}",
            mapping={
                "email": req.email,
                "plan": "free",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        pipe.sadd("admin:all_keys", key_hash)
        await pipe.execute()

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
    if await r.hexists(f"user:{req.email}", "pwd_hash"):
        raise HTTPException(status_code=400, detail="Email already registered")

    salt = secrets.token_hex(16)
    pwd_hash = _hash_password(req.password, salt)
    
    # Generate API key
    raw_key = f"vp_live_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)

    # Create Session Cookie
    session_id = secrets.token_urlsafe(64)

    async with r.pipeline() as pipe:
        # Store User
        pipe.hset(f"user:{req.email}", mapping={
            "pwd_hash": pwd_hash,
            "salt": salt,
            "api_key": raw_key
        })
        # Store API Key Profile
        pipe.hset(f"apikey:{key_hash}", mapping={
            "email": req.email,
            "plan": "free",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        pipe.sadd("admin:all_keys", key_hash)
        pipe.setex(f"session:{session_id}", 86400 * 30, req.email) # 30 days
        await pipe.execute()
    
    # Secure HTTPOnly Cookie
    is_https = "https" in str(request.url)
    response.set_cookie(key="vp_session", value=session_id, httponly=True, secure=is_https, samesite="lax", max_age=86400*30)
    
    return {"message": "Account created successfully"}

@app.post("/v1/auth/login", summary="Log in to an existing account")
async def auth_login(req: AuthRequest, response: Response, request: Request):
    user_data = await r.hgetall(f"user:{req.email}")
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    pwd_hash = _hash_password(req.password, user_data["salt"])
    if pwd_hash != user_data["pwd_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    # Create Session Cookie
    session_id = secrets.token_urlsafe(64)
    await r.setex(f"session:{session_id}", 86400 * 30, req.email)
    
    is_https = "https" in str(request.url)
    response.set_cookie(key="vp_session", value=session_id, httponly=True, secure=is_https, samesite="lax", max_age=86400*30)
    
    return {"message": "Logged in successfully"}

@app.post("/v1/auth/logout", summary="End the current session")
async def auth_logout(request: Request, response: Response):
    session_id = request.cookies.get("vp_session")
    if session_id:
        await r.delete(f"session:{session_id}")
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
        
    # We never return passwords or salts. Just the key and email.
    return {
        "email": email,
        "api_key": user_data.get("api_key")
    }

# ── Core: Risk Check ───────────────────────────────────────────────────────────
@app.post("/v1/risk-check", summary="Evaluate an order for fraud risk")
async def check_order(order: Order, key_data: dict = Depends(require_api_key)):
    start_time = time.perf_counter()
    uid, amount, address, client_ip = order.uid, order.amt, order.addr, order.ip
    reasons = []

    # Concurrent checks using pipelining and async execution
    import asyncio
    
    # 1. Parallel Data Fetch and Internal Processing
    velocity_task = _check_velocity(uid)
    sybil_task = _check_sybil(uid, address)
    price_task = _check_price_anomaly(uid, amount)
    trust_task = _get_trust_score(uid)
    ip_task = _check_ip_intelligence(client_ip)
    
    results = await asyncio.gather(velocity_task, sybil_task, price_task, trust_task, ip_task)
    
    is_velocity_flag, is_sybil_flag, (is_price_anomaly, avg, std_dev), trust_score, is_vpn_flag = results

    # 2. Advanced Risk Scoring (Rust)
    risk_score = vector_pulse.evaluate_weighted_risk(
        is_velocity_flag,
        is_sybil_flag,
        is_price_anomaly,
        trust_score,
        is_vpn_flag
    )

    if is_velocity_flag: reasons.append("HIGH_VELOCITY")
    if is_sybil_flag:    reasons.append("ADDRESS_SYBIL_DETECTED")
    if is_price_anomaly: reasons.append("HIGH_DEVIATION")
    if is_vpn_flag:      reasons.append("ANONYMOUS_IP_DETECTED")
    if trust_score < 30.0 and trust_score != 50.0: reasons.append("LOW_TRUST_SCORE")

    # Decision threshold logic
    is_risky = risk_score > 40.0
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
                "vpn": is_vpn_flag
            },
            "timestamp": time.time()
        }
        
        # Async background logging (simulated by await here for reliability)
        await _log_audit_event(risk_id, key_data.get("email"), context, action, order.shadow)

        async with r.pipeline() as pipe:
            pipe.setex(f"explain:{risk_id}", 86400 * 3, json.dumps(context)) # 3 day high-speed cache
            if is_risky:
                pipe.incrby("total_savings_inr", 70)
                status_label = "SHADOW_BLOCK" if order.shadow else "BLOCK"
                pipe.lpush("recent_blocks", f"{uid}: {', '.join(reasons)} ({status_label}: {risk_score:.0f}) [ID: {risk_id}]")
                pipe.ltrim("recent_blocks", 0, 49)
            
            if is_velocity_flag: pipe.incr("stat:velocity")
            if is_sybil_flag: pipe.incr("stat:sybil")
            if is_price_anomaly: pipe.incr("stat:price")
            if is_vpn_flag: pipe.incr("stat:vpn")
            
            pipe.incr(f"rep:{uid}:total")
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
        async with r.pipeline() as pipe:
            pipe.incr(f"rep:{uid}:delivered")
            pipe.incr(f"rep:{uid}:total")
            await pipe.execute()
        return {"uid": uid, "trust_score": round(await _get_trust_score(uid), 1), "status": "updated"}
    except Exception as e:
        logging.error(f"Failed to update delivery rep: {e}")
        return {"uid": uid, "status": "failed", "reason": "DB unreachable"}

# ── Observability: Explain Decisions ──────────────────────────────────────────
@app.get("/v1/explain/{risk_id}", summary="Get human-readable reasoning for a fraud decision")
async def explain_decision(risk_id: str, key_data: dict = Depends(require_api_key)):
    try:
        raw_data = await r.get(f"explain:{risk_id}")
        if not raw_data:
            # Fallback to persistent DB if Redis cache expired
            async with aiosqlite.connect(AUDIT_DB) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM risk_audit WHERE risk_id = ?", (risk_id,)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        raise HTTPException(status_code=404, detail="Risk ID not found")
                    context = {
                        "score": row["risk_score"],
                        "flags": row["reasons"].split(",") if row["reasons"] else [],
                        "metrics": json.loads(row["metrics"]),
                        "timestamp": row["timestamp"]
                    }
        else:
            context = json.loads(raw_data)
        
        # Build explanation
        narrative = []
        m = context["metrics"]
        if m["velocity"]: narrative.append(f"Multiple orders ({VELOCITY_MAX_ORDERS}+) detected in {VELOCITY_WINDOW_SECS}s window.")
        if m["vpn"]:      narrative.append("Transaction attempted via Data Center or Anonymous Proxy (VPN).")
        if m["price"]:    narrative.append("Transaction amount significantly deviates from historical average.")
        if m["sybil"]:    narrative.append("Multiple UIDs linked to same delivery address.")
        if m.get("trust", 50.0) < 30.0: narrative.append(f"Customer has low delivery score ({m['trust']:.0f}% success).")
        
        return {
            "risk_id": risk_id,
            "score": context["score"],
            "decision": "FORCE_PREPAID" if context["score"] > 40 else "ALLOW_COD",
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
    status: str # DELIVERED, RTO, FRAUD_CONFIRMED

@app.post("/v1/outcome", summary="Report the final outcome of a transaction (ML Feedback Loop)")
async def update_outcome(update: OutcomeUpdate, key_data: dict = Depends(require_api_key)):
    try:
        async with aiosqlite.connect(AUDIT_DB) as db:
            await db.execute(
                "UPDATE risk_audit SET outcome = ? WHERE risk_id = ?", 
                (update.status, update.risk_id)
            )
            await db.commit()
        return {"status": "success", "risk_id": update.risk_id, "updated_to": update.status}
    except Exception as e:
        logging.error(f"Outcome update failed: {e}")
        raise HTTPException(status_code=500, detail="Persistence layer error")
