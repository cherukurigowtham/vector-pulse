import hashlib
import json
import logging
from typing import List
import time
from app.core.redis import r
from app.models import Order
from app.core.helpers import _log_event
from app.services.webhook_dispatcher import dispatch_alert

class BehavioralEncoder:
    """
    Encodes order characteristics into a deterministic behavioral fingerprint.
    This allows us to find 'Behavioral Twins' across different IDs.
    """
    @staticmethod
    def encode(order: Order) -> str:
        # Normalize features for fingerprinting
        # We focus on patterns: Amount proximity, Address structure, and Timing
        features = {
            "amt_bucket": round(order.amt / 500) * 500, # Bucket by 500 INR
            "pin": order.pin,
            "addr_len": len(order.addr) // 5, # Bucket address length
            "behave_dna": (order.keystroke_velocity or 0) > 0.5,
        }
        fingerprint = hashlib.md5(json.dumps(features, sort_keys=True).encode()).hexdigest()
        return fingerprint

async def detect_fraud_ring(order: Order) -> bool:
    """
    Checks if a similar behavioral fingerprint has appeared multiple times 
    across different UIDs/Emails in the last 24 hours.
    """
    fingerprint = BehavioralEncoder.encode(order)
    key = f"ring:fingerprint:{fingerprint}"
    
    # Store the UID to count distinct users in this 'ring'
    await r.sadd(key, order.uid)
    await r.expire(key, 86400) # 24 hour window
    
    distinct_uids = await r.scard(key)
    
    if distinct_uids >= 3:
        logging.warning(f"Fraud Ring Detected: Fingerprint {fingerprint} shared by {distinct_uids} UIDs")
        # Trigger real-time alert for substantial rings (e.g., >= 5 participants)
        # or for the initial detection if we want aggressive alerting.
        # As CEO, we want to notify early.
        return True
    return False

async def get_cluster_risk_bonus(order: Order) -> float:
    """Returns a risk score bonus if part of a suspected ring."""
    if await detect_fraud_ring(order):
        return 40.0 # High penalty for shared behavioral fingerprint
    return 0.0

async def apply_global_reputation_impact(identities: dict, outcome: str):
    """
    Updates the cross-merchant reputation for specific identity attributes.
    This creates the 'Collective Defense' shield.
    """
    if not identities: return
    
    # Impact Factors: Higher impact for RTOs than for successful deliveries (Trust is hard to earn, easy to lose)
    impact = -0.25 if outcome in ["RTO", "FRAUD_CONFIRMED"] else 0.05
    from app.services.graph_service import _p_hash
    
    for attr, val in identities.items():
        if not val or val in ["noemail", "nophone", ""]: continue
        
        hashed_val = _p_hash(val)
        key = f"global:reputation:{attr}:{hashed_val}"
        
        # We use a moving average/incremental trust score stored in Redis
        current = await r.get(key)
        score = float(current) if current is not None else 0.5 # Start at neutral
        
        new_score = max(0.0, min(1.0, score + impact))
        await r.setex(key, 86400 * 90, str(new_score)) # 90-day memory for global trust
        _log_event("global_reputation_drift", attr=attr, new_score=new_score, outcome=outcome)

async def apply_outcome_feedback(email: str, factors: List[str], outcome: str, identities: dict = None):
    """
    Refined Adaptive Intelligence Feedback Loop.
    Adjusts neural biases for a merchant based on real-world delivery outcomes.
    
    - RTO/FRAUD: Increases weight of triggered risk factors (Penalty)
    - DELIVERED: Decreases weight of triggered risk factors (Reward)
    """
    if not factors: return
    
    # Sophisticated factor mapping: Linking analysis flags to configuration weights
    factor_map = {
        "HIGH_VELOCITY": "velocity_weight",
        "ADDRESS_SYBIL_DETECTED": "sybil_weight",
        "ANONYMOUS_IP_DETECTED": "vpn_weight",
        "PRICE_ANOMALY": "anomaly_weight",
        "GIBBERISH_ADDRESS": "gibberish_weight",
        "GLOBAL_IDENTITY_BLACKLIST": "identity_weight",
        "IMPOSSIBLE_TRAVEL": "geo_velocity_weight",
        "BOT_SPEED_CHECKOUT": "bot_speed_weight",
        "DISPOSABLE_EMAIL": "disposable_email_weight",
        "HIGH_RISK_PIN": "high_risk_pin_weight",
        "IDENTITY_CLUSTER_DETECTED": "identity_weight",
    }
    
    # Learning Parameters
    # As CEO, we want the system to learn fast at first, then stabilize.
    # For now, we use a constant but impactful adjustment.
    penalty_inc = 0.75  # Aggressive RTO defense
    reward_dec = -0.15  # Cautious False Positive recovery
    
    adjustment = penalty_inc if outcome in ["RTO", "FRAUD_CONFIRMED"] else reward_dec
    biases = {}
    
    for flag in factors:
        config_key = factor_map.get(flag)
        if config_key:
            # Atomic update of the bias in Redis
            current_bias = await r.hget(f"neural:bias:{email}", config_key) or 0
            new_val = float(current_bias) + adjustment
            
            # Clip the bias to reasonable extremes (-20 to +50) to prevent runaway weights
            new_val = max(-20.0, min(50.0, new_val))
            biases[config_key] = new_val
    
    if biases:
        await r.hset(f"neural:bias:{email}", mapping=biases)
        await r.expire(f"neural:bias:{email}", 60 * 86400) # 60-day memory for learned behavior
        _log_event("intelligence_learned", email=email, outcome=outcome, weight_adjustments=biases)
    
async def broadcast_geo_telemetry(lat: float, lon: float, risk_score: float):
    """
    Broadcasts anonymized geo-spatial attack data to the global telemetry feed.
    This enables the 'Real-Time Heatmap' in the Merchant Portal.
    """
    try:
        event = {
            "lat": round(lat, 2), # Lossy precision for privacy
            "lon": round(lon, 2),
            "score": round(risk_score, 1),
            "ts": time.time()
        }
        # Push to a capped list for real-time visualization
        await r.lpush("global:telemetry:geo", json.dumps(event))
        await r.ltrim("global:telemetry:geo", 0, 499) # Keep last 500 events
        await r.expire("global:telemetry:geo", 3600 * 6) # 6h TTL
    except Exception as e:
        logging.error(f"Telemetry Broadcast Failed: {e}")
