import hashlib
import re
import logging
from app.core.redis import r

def _preprocess_text(text: str) -> str:
    """Standardize text for semantic hashing."""
    if not text: return ""
    text = text.lower()
    # Remove common address suffixes to increase collision chance for similar addresses
    text = re.sub(r'\b(street|st|road|rd|avenue|ave|lane|ln|drive|dr|court|ct)\b', '', text)
    # Remove punctuation and extra whitespace
    text = re.sub(r'[^\w\s]', '', text)
    return " ".join(text.split())

def _get_shingles(text: str, k=3):
    """Generate k-shingles for the text."""
    return set(text[i:i+k] for i in range(len(text) - k + 1))

def generate_semantic_hash(address: str, name: str | None, email: str | None) -> str:
    """
    Advanced Pillar: Semantic Fraud Clustering.
    Generates a Locality-Sensitive Hash (LSH) for an order.
    Similar inputs will produce the same or highly similar hashes.
    """
    try:
        combined = f"{_preprocess_text(address)} {_preprocess_text(name or '')} {_preprocess_text(email or '')}"
        shingles = _get_shingles(combined)
        
        # SimHash implementation (simplified)
        v = [0] * 64
        for shingle in shingles:
            h = int(hashlib.md5(shingle.encode()).hexdigest(), 16)
            for i in range(64):
                bit = (h >> i) & 1
                if bit: v[i] += 1
                else: v[i] -= 1
        
        fingerprint = 0
        for i in range(64):
            if v[i] > 0:
                fingerprint |= (1 << i)
                
        return hex(fingerprint)
    except Exception as e:
        logging.error(f"Semantic hashing failed: {e}")
        return "0x0"

async def check_vector_cluster(order_hash: str):
    """
    Checks if this semantic cluster has been flagged as fraudulent by multiple merchants.
    """
    try:
        cluster_key = f"vector:cluster:{order_hash}"
        # A cluster is 'quarantined' if it has a high fraud-to-delivery ratio or explicit reports.
        is_quarantined = await r.sismember("global:quarantine", order_hash)
        return is_quarantined
    except Exception as e:
        logging.error(f"Cluster lookup failed: {e}")
        return False
