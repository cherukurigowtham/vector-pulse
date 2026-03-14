import os
import sys
import asyncio
import logging

try:
    import asyncpg
except ImportError:
    asyncpg = None

import aiosqlite

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def verify_postgres(url: str):
    if not url:
        logging.info("DATABASE_URL not set, skipping Postgres check.")
        return False
    
    if asyncpg is None:
        logging.error("asyncpg is not installed. Required for Postgres.")
        return False

    try:
        conn = await asyncpg.connect(url)
        logging.info("Successfully connected to Postgres.")
        
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_names = [r['table_name'] for r in tables]
        logging.info(f"Existing tables: {', '.join(table_names) if table_names else 'None'}")
        
        await conn.close()
        return True
    except Exception as e:
        logging.error(f"Postgres Connection Failed: {e}")
        return False

async def verify_sqlite(path: str):
    if not os.path.exists(path):
        logging.warning(f"SQLite file {path} does not exist yet.")
        return False
    
    try:
        async with aiosqlite.connect(path) as db:
            logging.info(f"Successfully connected to SQLite: {path}")
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
                tables = await cursor.fetchall()
                table_names = [t[0] for t in tables]
                logging.info(f"Existing tables: {', '.join(table_names) if table_names else 'None'}")
        return True
    except Exception as e:
        logging.error(f"SQLite Connection Failed: {e}")
        return False

async def main():
    db_url = os.getenv("DATABASE_URL", "").strip()
    audit_db = "audit_log.db"
    
    print("--- Infrastructure Verification ---")
    
    pg_ok = await verify_postgres(db_url)
    sqlite_ok = await verify_sqlite(audit_db)
    
    if not pg_ok and not sqlite_ok:
        print("\n[!] WARNING: No active database connections found.")
        sys.exit(1)
    
    print("\n[✓] Verification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
