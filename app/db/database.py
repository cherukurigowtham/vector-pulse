import json
import logging
import time
import os
from typing import Any, Optional
try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

class PostgresStore:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None
        self.backend = "postgres"

    async def create_invitation(self, team_id: str, email: str, role: str, inviter: str):
        invitation_id = f"invite_{int(time.time())}_{email.split('@')[0]}"
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO invitations (id, team_id, email, role, inviter, created_at, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, invitation_id, team_id, email, role, inviter, time.time(), "PENDING")
        return invitation_id

    async def get_team_invitations(self, team_id: str):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM invitations WHERE team_id = $1", team_id)
            return [dict(r) for r in rows]

    async def update_invitation_status(self, invite_id: str, status: str):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE invitations SET status = $1 WHERE id = $2", status, invite_id)

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
                    team_id TEXT,
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
                    team_id TEXT,
                    actor TEXT,
                    action TEXT,
                    previous_config TEXT,
                    new_config TEXT,
                    timestamp DOUBLE PRECISION
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    owner_email TEXT,
                    created_at DOUBLE PRECISION
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    team_id TEXT,
                    role TEXT,
                    joined_at DOUBLE PRECISION,
                    FOREIGN KEY (team_id) REFERENCES teams(id)
                )
            """)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def insert_risk_audit(self, p: dict):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO risk_audit (risk_id, uid, email, team_id, risk_score, decision, shadow_mode, reasons, metrics, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, p["risk_id"], p["uid"], p["email"], p.get("team_id"), p["risk_score"], p["decision"], p["shadow_mode"], p["reasons"], p["metrics"], p["timestamp"])

    async def update_outcome(self, risk_id: str, status: str, reason: str | None = None):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE risk_audit SET outcome = $1 WHERE risk_id = $2", status, risk_id)

    async def insert_risk_profile_audit(self, p: dict):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO risk_profile_audit (audit_id, email, team_id, actor, action, previous_config, new_config, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, p["audit_id"], p["email"], p.get("team_id"), p["actor"], p["action"], p["previous_config"], p["new_config"], p["timestamp"])

    async def delete_user_audits(self, email: str):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM risk_audit WHERE email = $1", email)
            await conn.execute("DELETE FROM risk_profile_audit WHERE email = $1", email)

    async def fetch_risk_audit(self, risk_id: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM risk_audit WHERE risk_id = $1", risk_id)
            return dict(row) if row else None

    async def fetch_risk_profile_audits(self, team_id: str, limit: int = 10):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM risk_profile_audit WHERE team_id = $1 ORDER BY timestamp DESC LIMIT $2", team_id, limit)
            return [dict(r) for r in rows]

    async def fetch_recent_risk_audits(self, team_id: str, limit: int = 12):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome FROM risk_audit WHERE team_id = $1 ORDER BY timestamp DESC LIMIT $2", team_id, limit)
            return [dict(r) for r in rows]

    async def fetch_all_merchant_audits(self, team_id: str, limit: int = 1000):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome, shadow_mode FROM risk_audit WHERE team_id = $1 ORDER BY timestamp DESC LIMIT $2", team_id, limit)
            return [dict(r) for r in rows]

    async def fetch_compliance_logs(self, team_id: str, start_ts: float, end_ts: float):
        async with self.pool.acquire() as conn:
            risk_rows = await conn.fetch("SELECT * FROM risk_audit WHERE team_id = $1 AND timestamp >= $2 AND timestamp <= $3 ORDER BY timestamp DESC", team_id, start_ts, end_ts)
            profile_rows = await conn.fetch("SELECT * FROM risk_profile_audit WHERE team_id = $1 AND timestamp >= $2 AND timestamp <= $3 ORDER BY timestamp DESC", team_id, start_ts, end_ts)
            return {
                "risk_events": [dict(r) for r in risk_rows],
                "profile_changes": [dict(r) for r in profile_rows]
            }

    async def get_user_role_and_team(self, email: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT role, team_id FROM users WHERE email = $1", email)
            return dict(row) if row else None

    async def create_team(self, team_id: str, name: str, owner_email: str):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO teams (id, name, owner_email, created_at) VALUES ($1, $2, $3, $4)", team_id, name, owner_email, time.time())
            await conn.execute("INSERT INTO users (email, team_id, role, joined_at) VALUES ($1, $2, $3, $4)", owner_email, team_id, "ADMIN", time.time())

    async def get_team_members(self, team_id: str):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT email, role, joined_at FROM users WHERE team_id = $1", team_id)
            return [dict(r) for r in rows]

    async def healthcheck(self) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except:
            return False

class SQLiteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backend = "sqlite"

    async def init(self):
        if aiosqlite is None:
            raise RuntimeError("aiosqlite not installed")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS risk_audit (
                    risk_id TEXT PRIMARY KEY,
                    uid TEXT,
                    email TEXT,
                    team_id TEXT,
                    risk_score REAL,
                    decision TEXT,
                    shadow_mode INTEGER,
                    reasons TEXT,
                    metrics TEXT,
                    timestamp REAL,
                    outcome TEXT DEFAULT 'PENDING'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS risk_profile_audit (
                    audit_id TEXT PRIMARY KEY,
                    email TEXT,
                    team_id TEXT,
                    actor TEXT,
                    action TEXT,
                    previous_config TEXT,
                    new_config TEXT,
                    timestamp REAL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    owner_email TEXT,
                    created_at REAL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    team_id TEXT,
                    role TEXT,
                    joined_at REAL,
                    FOREIGN KEY (team_id) REFERENCES teams(id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invitations (
                    id TEXT PRIMARY KEY,
                    team_id TEXT,
                    email TEXT,
                    role TEXT,
                    inviter TEXT,
                    created_at REAL,
                    status TEXT,
                    FOREIGN KEY (team_id) REFERENCES teams(id)
                )
            """)
            await db.commit()

    async def close(self):
        pass

    async def create_invitation(self, team_id: str, email: str, role: str, inviter: str):
        invitation_id = f"invite_{int(time.time())}_{email.split('@')[0]}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO invitations (id, team_id, email, role, inviter, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (invitation_id, team_id, email, role, inviter, time.time(), "PENDING"))
            await db.commit()
        return invitation_id

    async def get_team_invitations(self, team_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM invitations WHERE team_id = ?", (team_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def update_invitation_status(self, invite_id: str, status: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE invitations SET status = ? WHERE id = ?", (status, invite_id))
            await db.commit()

    async def insert_risk_audit(self, p: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO risk_audit (risk_id, uid, email, team_id, risk_score, decision, shadow_mode, reasons, metrics, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["risk_id"], p["uid"], p["email"], p.get("team_id"), p["risk_score"], p["decision"], p["shadow_mode"], p["reasons"], p["metrics"], p["timestamp"]))
            await db.commit()

    async def update_outcome(self, risk_id: str, status: str, reason: str | None = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE risk_audit SET outcome = ? WHERE risk_id = ?", (status, risk_id))
            await db.commit()

    async def insert_risk_profile_audit(self, p: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO risk_profile_audit (audit_id, email, team_id, actor, action, previous_config, new_config, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["audit_id"], p["email"], p.get("team_id"), p["actor"], p["action"], p["previous_config"], p["new_config"], p["timestamp"]))
            await db.commit()

    async def delete_user_audits(self, email: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM risk_audit WHERE email = ?", (email,))
            await db.execute("DELETE FROM risk_profile_audit WHERE email = ?", (email,))
            await db.commit()

    async def fetch_risk_audit(self, risk_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM risk_audit WHERE risk_id = ?", (risk_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def fetch_risk_profile_audits(self, team_id: str, limit: int = 10):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM risk_profile_audit WHERE team_id = ? ORDER BY timestamp DESC LIMIT ?", (team_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def fetch_recent_risk_audits(self, team_id: str, limit: int = 12):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome FROM risk_audit WHERE team_id = ? ORDER BY timestamp DESC LIMIT ?", (team_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def fetch_all_merchant_audits(self, team_id: str, limit: int = 1000):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT risk_id, uid, risk_score, decision, reasons, timestamp, outcome, shadow_mode FROM risk_audit WHERE team_id = ? ORDER BY timestamp DESC LIMIT ?", (team_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def fetch_compliance_logs(self, team_id: str, start_ts: float, end_ts: float):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM risk_audit WHERE team_id = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC", (team_id, start_ts, end_ts)) as cursor:
                risk_rows = await cursor.fetchall()
            async with db.execute("SELECT * FROM risk_profile_audit WHERE team_id = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp DESC", (team_id, start_ts, end_ts)) as cursor:
                profile_rows = await cursor.fetchall()
            return {
                "risk_events": [dict(r) for r in risk_rows],
                "profile_changes": [dict(r) for r in profile_rows]
            }

    async def get_user_role_and_team(self, email: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT role, team_id FROM users WHERE email = ?", (email,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def create_team(self, team_id: str, name: str, owner_email: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO teams (id, name, owner_email, created_at) VALUES (?, ?, ?, ?)", (team_id, name, owner_email, time.time()))
            await db.execute("INSERT INTO users (email, team_id, role, joined_at) VALUES (?, ?, ?, ?)", (owner_email, team_id, "ADMIN", time.time()))
            await db.commit()

    async def get_team_members(self, team_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT email, role, joined_at FROM users WHERE team_id = ?", (team_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def healthcheck(self) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
            return True
        except:
            return False

from app.core.config import DATABASE_URL, AUDIT_DB

if DATABASE_URL:
    AUDIT_STORE = PostgresStore(DATABASE_URL)
else:
    logging.info(f"Using SQLite Fallback: {AUDIT_DB}")
    AUDIT_STORE = SQLiteStore(AUDIT_DB)
