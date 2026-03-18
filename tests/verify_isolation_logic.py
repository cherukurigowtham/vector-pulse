import asyncio
import uuid
import time
from app.db.database import AUDIT_STORE

async def verify_isolation():
    print("🚀 Starting Multi-Tenancy Isolation Verification...")
    await AUDIT_STORE.init()
    
    # 1. Create two teams
    team1_id = f"team_{uuid.uuid4().hex[:4]}"
    team2_id = f"team_{uuid.uuid4().hex[:4]}"
    email1 = f"admin1_{uuid.uuid4().hex[:4]}@example.com"
    email2 = f"admin2_{uuid.uuid4().hex[:4]}@example.com"
    
    print(f"Creating Team 1: {team1_id} for {email1}")
    await AUDIT_STORE.create_team(team1_id, "Team 1", email1)
    print(f"Creating Team 2: {team2_id} for {email2}")
    await AUDIT_STORE.create_team(team2_id, "Team 2", email2)
    
    # 2. Insert audits for Team 1
    print("Inserting audits for Team 1...")
    await AUDIT_STORE.insert_risk_audit({
        "risk_id": f"r1_{uuid.uuid4().hex[:4]}", "uid": "u1", "email": email1, "team_id": team1_id,
        "risk_score": 10.0, "decision": "ALLOW_COD", "shadow_mode": 0,
        "reasons": "", "metrics": "{}", "timestamp": time.time()
    })
    
    # 3. Insert audits for Team 2
    print("Inserting audits for Team 2...")
    await AUDIT_STORE.insert_risk_audit({
        "risk_id": f"r2_{uuid.uuid4().hex[:4]}", "uid": "u2", "email": email2, "team_id": team2_id,
        "risk_score": 90.0, "decision": "FORCE_PREPAID", "shadow_mode": 0,
        "reasons": "HIGH_RISK", "metrics": "{}", "timestamp": time.time()
    })
    
    # 4. Verify Fetch Isolation
    print("Verifying isolation...")
    t1_audits = await AUDIT_STORE.fetch_recent_risk_audits(team1_id)
    t2_audits = await AUDIT_STORE.fetch_recent_risk_audits(team2_id)
    
    print(f"Team 1 Audits Count: {len(t1_audits)}")
    print(f"Team 2 Audits Count: {len(t2_audits)}")
    
    assert len(t1_audits) >= 1
    assert all(a['risk_id'].startswith('r1_') for a in t1_audits if a['risk_id'].startswith('r1_') or a['risk_id'].startswith('r2_'))
    
    assert len(t2_audits) >= 1
    assert all(a['risk_id'].startswith('r2_') for a in t2_audits if a['risk_id'].startswith('r1_') or a['risk_id'].startswith('r2_'))
    
    print("✅ Multi-Tenancy Data Isolation Verified in DB!")

if __name__ == "__main__":
    asyncio.run(verify_isolation())
