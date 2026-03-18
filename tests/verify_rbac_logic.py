import asyncio
import uuid
import time
from app.db.database import AUDIT_STORE
from app.core.redis import r

async def verify_rbac():
    print("🚀 Starting RBAC Verification...")
    await AUDIT_STORE.init()
    
    email = f"test_{uuid.uuid4().hex[:4]}@example.com"
    team_id = f"team_{uuid.uuid4().hex[:4]}"
    
    # 1. Test Team Creation
    print(f"Creating team {team_id} for {email}...")
    await AUDIT_STORE.create_team(team_id, "Test Team", email)
    
    # 2. Verify User Role in DB
    user_info = await AUDIT_STORE.get_user_role_and_team(email)
    print(f"DB Check - User Role: {user_info['role']}, Team: {user_info['team_id']}")
    assert user_info['role'] == 'ADMIN'
    assert user_info['team_id'] == team_id
    
    # 3. Test Team Members
    members = await AUDIT_STORE.get_team_members(team_id)
    print(f"Team Members: {[m['email'] for m in members]}")
    assert len(members) == 1
    assert members[0]['email'] == email
    
    print("✅ RBAC Logic Verified in DB!")

if __name__ == "__main__":
    asyncio.run(verify_rbac())
