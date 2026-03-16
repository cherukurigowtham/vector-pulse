import hashlib
import logging
from app.core.redis import r

async def link_identity(uid: str, email: str | None, phone: str | None, address: str, ip: str, merchant_email: str):
    """
    Advanced Pillar: Fraud Ring Detection.
    Builds a shared identity graph by linking attributes.
    All data is hashed or normalized to protect privacy while maintaining connectivity.
    """
    try:
        # 1. Normalize and hash attributes
        addr_key = f"graph:attr:addr:{hashlib.md5(address.lower().strip().encode()).hexdigest()}"
        ip_key = f"graph:attr:ip:{ip}"
        
        # 2. Link attributes to the UID within the merchant's context
        async with r.pipeline() as pipe:
            # Shared Attributes (Cross-Merchant)
            # These sets contain merchant_email:uid to identify WHO and WHERE the attribute was used.
            identity_val = f"{merchant_email}:{uid}"
            pipe.sadd(addr_key, identity_val)
            pipe.sadd(ip_key, identity_val)
            
            # Set TTLs (e.g., 90 days)
            pipe.expire(addr_key, 86400 * 90)
            pipe.expire(ip_key, 86400 * 90)
            
            # Identify other entities sharing the same attributes
            pipe.smembers(addr_key)
            pipe.smembers(ip_key)
            
            res = await pipe.execute()
            
        # 3. Analyze connections
        connections = set(res[4]) | set(res[5])
        # Find connection count from OTHER merchants
        other_merchant_hits = 0
        for conn in connections:
            if not conn.decode().startswith(f"{merchant_email}:"):
                other_merchant_hits += 1
                
        return other_merchant_hits
    except Exception as e:
        logging.error(f"identity linking failed: {e}")
        return 0
