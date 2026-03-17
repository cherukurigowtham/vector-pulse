import hashlib
import logging
from app.core.redis import r
from app.core.config import GLOBAL_PULSE_SALT

def _p_hash(val: str) -> str:
    """Pulse Hash: Secure, salted fingerprinting for the Global Pulse network."""
    return hashlib.sha256(f"{GLOBAL_PULSE_SALT}:{val.lower().strip()}".encode()).hexdigest()

async def get_global_reputation(attribute_type: str, hashed_value: str) -> float:
    """
    Fetches the normalized reputation score (0.0 to 1.0) for a global attribute.
    1.0 = High Trust (Consistent clean history)
    0.0 = Low Trust (History of RTOs/Fraud)
    0.5 = Neutral (New or low signal)
    """
    try:
        score = await r.get(f"global:reputation:{attribute_type}:{hashed_value}")
        return float(score) if score is not None else 0.5
    except:
        return 0.5

async def link_identity(uid: str, email: str | None, phone: str | None, address: str, ip: str, merchant_email: str):
    """
    Advanced Pillar: Fraud Ring Detection.
    Builds a shared identity graph by linking attributes.
    All data is hashed or normalized to protect privacy while maintaining connectivity.
    """
    try:
        # 1. Salted Fingerprinting
        addr_hash = _p_hash(address)
        email_hash = _p_hash(email or "noemail")
        phone_hash = _p_hash(phone or "nophone")
        
        addr_key = f"graph:attr:addr:{addr_hash}"
        ip_key = f"graph:attr:ip:{ip}"
        email_key = f"graph:attr:email:{email_hash}"
        phone_key = f"graph:attr:phone:{phone_hash}"
        
        # 2. Link attributes to the UID within the merchant's context
        async with r.pipeline() as pipe:
            identity_val = f"{merchant_email}:{uid}"
            for k in [addr_key, ip_key, email_key, phone_key]:
                pipe.sadd(k, identity_val)
                pipe.expire(k, 86400 * 90) # 90-day memory
            
            # Identify other entities sharing the same attributes
            pipe.smembers(addr_key)
            pipe.smembers(ip_key)
            pipe.smembers(email_key)
            pipe.smembers(phone_key)
            
            res = await pipe.execute()
            
        # 3. Analyze connections (Total of 8 pipeline results: 4 sadd/expire, 4 smembers)
        # Note: Pipe results depend on implementation. Sadd/Expire return status.
        # res looks like [int, bool, int, bool, int, bool, int, bool, set, set, set, set]
        connections = set()
        for i in range(8, 12):
            connections |= set(res[i])
            
        # Find connection count from OTHER merchants
        other_merchant_hits = 0
        for conn in connections:
            if not conn.startswith(f"{merchant_email}:"):
                other_merchant_hits += 1
        
        # 4. Fetch Global Pulse Signals
        # These are used by risk_service to adjust weights
        reputation_tasks = [
            get_global_reputation("addr", addr_hash),
            get_global_reputation("email", email_hash),
            get_global_reputation("phone", phone_hash)
        ]
        import asyncio
        reputations = await asyncio.gather(*reputation_tasks)
        
        return {
            "hits": other_merchant_hits,
            "reputation": {
                "addr": reputations[0],
                "email": reputations[1],
                "phone": reputations[2]
            }
        }
    except Exception as e:
        logging.error(f"identity linking failed: {e}")
        return 0
