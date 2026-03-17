import redis
import os
import sys
from app.core.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_SSL, ADMIN_SECRET_KEY
from app.core.helpers import _log_event

def reset():
    print("--- Vector-Pulse Admin Reset Tool ---")
    
    # Check for reset confirmation string
    confirm_text = os.getenv("VECTOR_PULSE_RESET_CONFIRM", "")
    if confirm_text != "DELETE_ALL_DATA":
        print("[!] Error: RESET_CONFIRM env var must be set to 'DELETE_ALL_DATA'.")
        sys.exit(1)

    # Hardened Auth: Require the actual ADMIN_SECRET_KEY
    auth_key = os.getenv("VECTOR_PULSE_ADMIN_KEY", "")
    if auth_key != ADMIN_SECRET_KEY:
        print("[!] Unauthorized: VECTOR_PULSE_ADMIN_KEY does not match system secret.")
        _log_event("admin_reset_failed", reason="invalid_secret_key")
        sys.exit(1)

    r = redis.Redis(
        host=REDIS_HOST, 
        port=REDIS_PORT, 
        password=REDIS_PASSWORD, 
        ssl=REDIS_SSL,
        db=0
    )

    try:
        print(f"Connecting to {REDIS_HOST}...")
        r.flushdb()
        print("[✓] Redis database flushed.")
        
        # Audit Log the destruction
        _log_event(
            "admin_reset_success", 
            performed_by="system_admin",
            target="redis_db_0"
        )
    except Exception as e:
        print(f"[!] Reset failed: {e}")
        _log_event("admin_reset_error", error=str(e))

if __name__ == "__main__":
    reset()
