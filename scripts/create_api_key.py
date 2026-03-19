import asyncio
import secrets
import hashlib
from app.core.redis import r
from app.core.helpers import _key_metadata, PRIMARY_ADMIN_EMAIL

async def create_key():
    raw_key = f"vp_live_{secrets.token_hex(16)}"
    
    # 1. Generate Legacy Hash (SHA256) for lookup
    legacy_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    # 2. Generate PBKDF2 metadata (for more secure second-level check)
    metadata = _key_metadata(raw_key)
    key_hash = metadata["key_hash"]
    
    profile = {
        "email": PRIMARY_ADMIN_EMAIL,
        "key_hash": key_hash, # This is the PBKDF2 hash
        "salt": metadata["salt"],
        "plan": "scale",
        "status": "active",
        "team_id": "system"
    }
    
    # Store by legacy hash
    await r.hset(f"apikey:{legacy_hash}", mapping=profile)
    await r.set(f"emailkey:{PRIMARY_ADMIN_EMAIL}", legacy_hash)
    await r.sadd("admin:all_keys", legacy_hash)
    
    print(f"SUCCESS: Created API key for {PRIMARY_ADMIN_EMAIL}")
    print(f"API KEY: {raw_key}")

if __name__ == "__main__":
    asyncio.run(create_key())
