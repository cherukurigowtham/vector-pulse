from fastapi import FastAPI
import redis
import vector_pulse
import os

app = FastAPI(title="Vector-Pulse: RTO Shield Enterprise")
r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0, decode_responses=True)

# Configuration: Toggle Shadow Mode to prove ROI before going live
SHADOW_MODE = False 

@app.post("/v1/risk-check")
async def check_order(uid: str, amount: float, address: str, pincode: str):
    reasons = []
    
    # 1. Location Risk (New Feature)
    loc_risk = r.get(f"pincode_risk:{pincode}")
    if loc_risk and float(loc_risk) > 0.8:
        reasons.append("HIGH_RTO_ZONE")

    # 2. Sybil Check (Address Hash)
    address_hash = hash(address.strip().lower())
    r.sadd(f"addr:{address_hash}", uid)
    if r.scard(f"addr:{address_hash}") > 3:
        reasons.append("ADDRESS_SYBIL_DETECTED")

    # 3. Rust-Powered Trust Score
    delivered = int(r.get(f"user:{uid}:delivered") or 0)
    total = int(r.get(f"user:{uid}:total") or 0)
    trust_score = vector_pulse.calculate_trust_score(delivered, total)
    if trust_score < 40:
        reasons.append("POOR_PURCHASE_HISTORY")

    # 4. Final Decision
    is_risky = len(reasons) > 0
    action = "FORCE_PREPAID" if (is_risky and not SHADOW_MODE) else "ALLOW_COD"
    
    if is_risky:
        r.incrby("total_savings_inr", 70) # Track potential savings

    return {
        "uid": uid,
        "decision": action,
        "risk_factors": reasons,
        "is_shadow_mode": SHADOW_MODE,
        "savings_contribution": 70 if is_risky else 0
    }
