import pytest
import httpx
import asyncio
from app.main import app
from app.core.redis import r
from app.db.database import AUDIT_STORE

@pytest.mark.asyncio
async def test_rbac_and_isolation():
    # 1. Setup - Create two teams and two users
    team1_id = "team_1"
    team2_id = "team_2"
    user1_email = "admin1@example.com"
    user2_email = "viewer2@example.com"
    
    await AUDIT_STORE.init()
    await AUDIT_STORE.create_team(team1_id, "Team One", user1_email)
    
    # Manually create second team and user with VIEWER role
    await AUDIT_STORE.db.execute("INSERT INTO teams (id, name, owner_email, created_at) VALUES (?, ?, ?, ?)", (team2_id, "Team Two", user2_email, 0))
    await AUDIT_STORE.db.execute("INSERT INTO users (email, team_id, role, joined_at) VALUES (?, ?, ?, ?)", (user2_email, team2_id, "VIEWER", 0))
    await AUDIT_STORE.db.commit()
    
    # 2. Test Data Isolation - Insert audits for team 1
    await AUDIT_STORE.insert_risk_audit({
        "risk_id": "r1", "uid": "u1", "email": user1_email, "team_id": team1_id,
        "risk_score": 10.0, "decision": "ALLOW_COD", "shadow_mode": 0,
        "reasons": "", "metrics": "{}", "timestamp": 100.0
    })
    
    # Insert audits for team 2
    await AUDIT_STORE.insert_risk_audit({
        "risk_id": "r2", "uid": "u2", "email": user2_email, "team_id": team2_id,
        "risk_score": 90.0, "decision": "FORCE_PREPAID", "shadow_mode": 0,
        "reasons": "HIGH_RISK", "metrics": "{}", "timestamp": 200.0
    })
    
    # 3. Verify Isolation - Team 1 should only see r1
    t1_audits = await AUDIT_STORE.fetch_recent_risk_audits(team1_id)
    assert len(t1_audits) == 1
    assert t1_audits[0]["risk_id"] == "r1"
    
    t2_audits = await AUDIT_STORE.fetch_recent_risk_audits(team2_id)
    assert len(t2_audits) == 1
    assert t2_audits[0]["risk_id"] == "r2"
    
    print("✅ Multi-Tenancy Data Isolation Verified!")

if __name__ == "__main__":
    asyncio.run(test_rbac_and_isolation())
