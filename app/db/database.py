import aiosqlite
import json
import logging
import time
from typing import Any, Optional
try:
    import asyncpg
except ImportError:
    asyncpg = None

class PostgresStore:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None
        self.backend = "postgres"

    async def init(self):
        if asyncpg is None:
            raise RuntimeError("DATABASE_URL set but asyncpg not installed")
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS risk_audit (
                    risk_id TEXT PRIMARY KEY,
                    uid TEXT,
                    email TEXT,
                    risk_score DOUBLE PRECISION,
                    decision TEXT,
                    shadow_mode INTEGER,
                    reasons TEXT,
                    metrics TEXT,
                    timestamp DOUBLE PRECISION,
                    outcome TEXT DEFAULT 'PENDING'
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS risk_profile_audit (
                    audit_id TEXT PRIMARY KEY,
                    email TEXT,
                    actor TEXT,
                    action TEXT,
                    previous_config TEXT,
                    new_config TEXT,
                    timestamp DOUBLE PRECISION
                )
            """)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def insert_risk_audit(self, p: dict):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO risk_audit (risk_id, uid, email, risk_score, decision, shadow_mode, reasons, metrics, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, p["risk_id"], p["uid"], p["email"], p["risk_score"], p["decision"], p["shadow_mode"], p["reasons"], p["metrics"], p["timestamp"])

    async def update_outcome(self, risk_id: str, status: str, reason: str | None = None):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE risk_audit SET outcome = $1 WHERE risk_id = $2", status, risk_id)

    async def insert_risk_profile_audit(self, p: dict):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO risk_profile_audit (audit_id, email, actor, action, previous_config, new_config, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, p["audit_id"], p["email"], p["actor"], p["action"], p["previous_config"], p["new_config"], p["timestamp"])

    async def delete_user_audits(self, email: str):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM risk_audit WHERE email = $1", email)
            await conn.execute("DELETE FROM risk_profile_audit WHERE email = $1", email)

    async def fetch_risk_audit(self, risk_id: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM risk_audit WHERE risk_id = $1", risk_id)
            return dict(row) if row else None

    async def update_outcome(self, risk_id: str, status: str):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE risk_audit SET outcome = $1 WHERE risk_id = $2", status, risk_id)

    async def fetch_risk_profile_audits(self, email: str, limit: int = 10):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM risk_profile_audit WHERE email = $1 ORDER BY timestamp DESC LIMIT $2", email, limit)
            return [dict(r) for r in rows]

    async def fetch_recent_risk_audits(self, email: str, limit: int = 12):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome FROM risk_audit WHERE email = $1 ORDER BY timestamp DESC LIMIT $2", email, limit)
            return [dict(r) for r in rows]

    async def fetch_all_merchant_audits(self, email: str, limit: int = 1000):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome, shadow_mode FROM risk_audit WHERE email = $1 ORDER BY timestamp DESC LIMIT $2", email, limit)
            return [dict(r) for r in rows]

    async def fetch_compliance_logs(self, email: str, start_ts: float, end_ts: float):
        async with self.pool.acquire() as conn:
            # Aggregate both risk decisions and profile audits for compliance reporting
            risk_rows = await conn.fetch("SELECT * FROM risk_audit WHERE email = $1 AND timestamp >= $2 AND timestamp <= $3 ORDER BY timestamp DESC", email, start_ts, end_ts)
            profile_rows = await conn.fetch("SELECT * FROM risk_profile_audit WHERE email = $1 AND timestamp >= $2 AND timestamp <= $3 ORDER BY timestamp DESC", email, start_ts, end_ts)
            return {
                "risk_events": [dict(r) for r in risk_rows],
                "profile_changes": [dict(r) for r in profile_rows]
            }

    async def healthcheck(self) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except:
            return False

class SQLiteStore:
    def __init__(self, path: str):
        self.path = path
        self.db = None
        self.backend = "sqlite"

    async def init(self):
        # Connection pooling: Keep one connection open for the lifetime of the app
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS risk_audit (
                risk_id TEXT PRIMARY KEY,
                uid TEXT,
                email TEXT,
                risk_score REAL,
                decision TEXT,
                shadow_mode INTEGER,
                reasons TEXT,
                metrics TEXT,
                timestamp REAL,
                outcome TEXT DEFAULT 'PENDING'
            )
        """)
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS risk_profile_audit (
                audit_id TEXT PRIMARY KEY,
                email TEXT,
                actor TEXT,
                action TEXT,
                previous_config TEXT,
                new_config TEXT,
                timestamp REAL
            )
        """)
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()

    async def insert_risk_audit(self, p: dict):
        await self.db.execute("""
            INSERT INTO risk_audit (risk_id, uid, email, risk_score, decision, shadow_mode, reasons, metrics, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (p["risk_id"], p["uid"], p["email"], p["risk_score"], p["decision"], p["shadow_mode"], p["reasons"], p["metrics"], p["timestamp"]))
        await self.db.commit()

    async def insert_risk_profile_audit(self, p: dict):
        await self.db.execute("""
            INSERT INTO risk_profile_audit (audit_id, email, actor, action, previous_config, new_config, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (p["audit_id"], p["email"], p["actor"], p["action"], p["previous_config"], p["new_config"], p["timestamp"]))
        await self.db.commit()

    async def delete_user_audits(self, email: str):
        await self.db.execute("DELETE FROM risk_audit WHERE email = ?", (email,))
        await self.db.execute("DELETE FROM risk_profile_audit WHERE email = ?", (email,))
        await self.db.commit()

    async def fetch_risk_audit(self, risk_id: str):
        if not self.db: return None
        async with self.db.execute("SELECT * FROM risk_audit WHERE risk_id = ?", (risk_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_outcome(self, risk_id: str, status: str, reason: str | None = None):
        if not self.db: return
        await self.db.execute("UPDATE risk_audit SET outcome = ? WHERE risk_id = ?", (status, risk_id))
        await self.db.commit()

    async def fetch_risk_profile_audits(self, email: str, limit: int = 10):
        async with self.db.execute("SELECT * FROM risk_profile_audit WHERE email = ? ORDER BY timestamp DESC LIMIT ?", (email, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def fetch_recent_risk_audits(self, email: str, limit: int = 12):
        async with self.db.execute("SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome FROM risk_audit WHERE email = ? ORDER BY timestamp DESC LIMIT ?", (email, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def fetch_all_merchant_audits(self, email: str, limit: int = 1000):
        async with self.db.execute("SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome, shadow_mode FROM risk_audit WHERE email = ? ORDER BY timestamp DESC LIMIT ?", (email, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def fetch_compliance_logs(self, email: str, start_ts: float, end_ts: float):
        async with self.db.execute("SELECT * FROM risk_audit WHERE email = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC", (email, start_ts, end_ts)) as cursor:
            risk_rows = await cursor.fetchall()
        async with self.db.execute("SELECT * FROM risk_profile_audit WHERE email = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC", (email, start_ts, end_ts)) as cursor:
            profile_rows = await cursor.fetchall()
        return {
            "risk_events": [dict(r) for r in risk_rows],
            "profile_changes": [dict(r) for r in profile_rows]
        }

    async def healthcheck(self) -> bool:
        try:
            async with self.db.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            return True
        except:
            return False

from app.core.config import DATABASE_URL, AUDIT_DB
if DATABASE_URL:
    AUDIT_STORE = PostgresStore(DATABASE_URL)
else:
    AUDIT_STORE = SQLiteStore(AUDIT_DB)
