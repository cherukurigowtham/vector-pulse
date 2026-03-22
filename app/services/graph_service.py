import hashlib
import logging
from app.core.redis import r, rk
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
        score = await r.get(rk(f"global:reputation:{attribute_type}:{hashed_value}"))
        return float(score) if score is not None else 0.5
    except:
        return 0.5

async def analyze_subgraph(uids: list[str]) -> dict:
    """
    GNN Pillar: Subgraph Scoring.
    Evaluates the risk of a cluster based on the collective behavior of interconnected identities.
    """
    if not uids: return {"cluster_risk": 0.5, "is_fraud_ring": False}
    
    # In a real GNN, we'd run a forward pass on the adjacency matrix. 
    # Here, we simulate by checking the aggregate trust of all connected nodes.
    total_reputation = 0
    fraud_signals = 0
    
    for uid_pair in uids:
        # Expected format: "merchant:uid"
        parts = uid_pair.split(":", 1)
        if len(parts) < 2: continue
        
        # Simulate a node reputation lookup
        # In a real system, this would be a persistent node_store
        trust = await r.get(rk(f"graph:node:trust:{uid_pair}"))
        val = float(trust) if trust else 0.5
        total_reputation += val
        if val < 0.3: fraud_signals += 1
            
    avg_trust = total_reputation / len(uids)
    is_ring = fraud_signals > 2 or avg_trust < 0.4
    
    return {
        "cluster_size": len(uids),
        "avg_trust": avg_trust,
        "is_fraud_ring": is_ring,
        "threat_level": "CRITICAL" if is_ring else "STABLE"
    }

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
        
        addr_key = rk(f"graph:attr:addr:{addr_hash}")
        ip_key = rk(f"graph:attr:ip:{ip}")
        email_key = rk(f"graph:attr:email:{email_hash}")
        phone_key = rk(f"graph:attr:phone:{phone_hash}")
        
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
            
        # 3. Analyze connections
        connections = set()
        for i in range(8, 12):
            connections |= set(res[i])
            
        # Find connection count from OTHER merchants
        other_merchant_hits = 0
        for conn in connections:
            if not conn.startswith(f"{merchant_email}:"):
                other_merchant_hits += 1
        
        # 4. Phase 12: Cluster GNN Intelligence
        cluster_analysis = await analyze_subgraph(list(connections))
        
        # 5. Fetch Global Pulse Signals
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
            },
            "cluster": cluster_analysis
        }
    except Exception as e:
        logging.error(f"identity linking failed: {e}")
        return {"hits": 0, "reputation": {}, "cluster": {}}
