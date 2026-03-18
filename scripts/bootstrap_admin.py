import asyncio
import secrets
from app.core.redis import r
from app.core.helpers import PRIMARY_ADMIN_EMAIL
from app.core.security import _hash_password

async def bootstrap():
    print(f"--- Bootstrapping Admin Account: {PRIMARY_ADMIN_EMAIL} ---")
    
    password = "admin123" # Temporary default password
    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)

    # 1. Initialize Admin User in Redis
    user_key = f"user:{PRIMARY_ADMIN_EMAIL}"
    user_data = {
        "email": PRIMARY_ADMIN_EMAIL,
        "role": "ADMIN",
        "team_id": "system",
        "name": "Global Administrator",
        "status": "active",
        "password_hash": password_hash,
        "salt": salt
    }
    
    await r.hset(user_key, mapping=user_data)
    print(f"SUCCESS: Created admin user at {user_key} with password: {password}")
    
    # 2. Add to team index
    await r.sadd("team:system:members", PRIMARY_ADMIN_EMAIL)
    print("SUCCESS: Added admin to system team.")

if __name__ == "__main__":
    asyncio.run(bootstrap())
