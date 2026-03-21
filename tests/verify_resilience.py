import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.core.redis import r, rk
from app.db.database import AUDIT_STORE, SQLiteStore, PostgresStore

async def verify_redis_isolation():
    print("--- Verifying Redis Isolation ---")
    test_key = "isolation_test"
    test_val = "isolated_data"
    
    # Set with current prefix
    prefixed_key = rk(test_key)
    print(f"Setting key: {prefixed_key}")
    await r.set(prefixed_key, test_val)
    
    # Verify it's there
    val = await r.get(prefixed_key)
    assert val == test_val, f"Expected {test_val}, got {val}"
    
    # Try to get without prefix (should be None or different)
    raw_val = await r.get(test_key)
    print(f"Raw key '{test_key}' value: {raw_val}")
    assert raw_val != test_val, "Raw key should not match prefixed key if isolation is working"
    
    print("Redis isolation check PASSED.")

async def verify_sqlite_fallback():
    print("\n--- Verifying SQLite Fallback ---")
    # This depends on how the module was loaded.
    # Since we imported it already, it should be initialized based on current ENV.
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set. AUDIT_STORE should be SQLiteStore.")
        assert isinstance(AUDIT_STORE, SQLiteStore), f"Expected SQLiteStore, got {type(AUDIT_STORE)}"
    else:
        print(f"DATABASE_URL is set to {db_url}. AUDIT_STORE should be PostgresStore.")
        assert isinstance(AUDIT_STORE, PostgresStore), f"Expected PostgresStore, got {type(AUDIT_STORE)}"
    
    print("Database fallback check PASSED.")

async def main():
    try:
        await verify_redis_isolation()
        await verify_sqlite_fallback()
        print("\nALL VERIFICATIONS PASSED!")
    except AssertionError as e:
        print(f"\nVERIFICATION FAILED: {e}")
    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
