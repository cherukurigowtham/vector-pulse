import asyncio
import sys
import os
sys.path.append(os.getcwd())

from app.core.redis import r
from app.core.security import get_current_user_role

ADMIN_EMAIL = "admin_test@vantix.com"
ANALYST_EMAIL = "analyst_test@vantix.com"
VIEWER_EMAIL = "viewer_test@vantix.com"

async def setup_test_users():
    print("Setting up test users in Redis...")
    await r.hset(f"user:{ADMIN_EMAIL}", mapping={"role": "ADMIN", "plan": "enterprise"})
    await r.hset(f"user:{ANALYST_EMAIL}", mapping={"role": "ANALYST", "plan": "enterprise"})
    await r.hset(f"user:{VIEWER_EMAIL}", mapping={"role": "VIEWER", "plan": "enterprise"})
    
    await r.setex("session:admin_session_token", 3600, ADMIN_EMAIL)
    await r.setex("session:analyst_session_token", 3600, ANALYST_EMAIL)
    await r.setex("session:viewer_session_token", 3600, VIEWER_EMAIL)
    print("  ✅ Users created: ADMIN, ANALYST, VIEWER")

async def verify_role_reading():
    print("\nVerifying role-reading from sessions...")
    
    class MockRequest:
        def __init__(self, session_token):
            self.cookies = {"vp_session": session_token}
    
    admin_role = await get_current_user_role(MockRequest("admin_session_token"))
    analyst_role = await get_current_user_role(MockRequest("analyst_session_token"))
    viewer_role = await get_current_user_role(MockRequest("viewer_session_token"))
    anon_role = await get_current_user_role(MockRequest("invalid_nonexistent_token"))
    
    assert admin_role == "ADMIN", f"Expected ADMIN, got {admin_role}"
    assert analyst_role == "ANALYST", f"Expected ANALYST, got {analyst_role}"
    assert viewer_role == "VIEWER", f"Expected VIEWER, got {viewer_role}"
    assert anon_role == "ANONYMOUS", f"Expected ANONYMOUS, got {anon_role}"
    
    print("  ✅ ADMIN role correctly identified")
    print("  ✅ ANALYST role correctly identified")
    print("  ✅ VIEWER role correctly identified")
    print("  ✅ Anonymous session correctly identified as ANONYMOUS")

async def verify_team_membership():
    print("\nVerifying team domain matching logic...")
    domain = ADMIN_EMAIL.split("@")[-1]
    all_users = await r.keys("user:*")
    
    team_members = []
    for u_key in all_users:
        u_email = u_key.split(":")[-1]
        if u_email.endswith(f"@{domain}"):
            u_data = await r.hgetall(f"user:{u_email}")
            team_members.append({
                "email": u_email,
                "role": u_data.get("role", "ANALYST"),
            })
    
    emails = [m["email"] for m in team_members]
    assert ADMIN_EMAIL in emails, f"ADMIN not found in team: {emails}"
    assert ANALYST_EMAIL in emails, f"ANALYST not found in team: {emails}"
    assert VIEWER_EMAIL in emails, f"VIEWER not found in team: {emails}"
    
    print(f"  ✅ Team '{domain}' has {len(team_members)} members")
    for m in team_members:
        print(f"     - {m['email']} [{m['role']}]")

async def teardown_test_users():
    await r.delete(f"user:{ADMIN_EMAIL}", f"user:{ANALYST_EMAIL}", f"user:{VIEWER_EMAIL}")
    await r.delete("session:admin_session_token", "session:analyst_session_token", "session:viewer_session_token")
    print("\nTest users cleaned up.")

async def verify():
    print("=" * 50)
    print("PHASE 24: ENTERPRISE RBAC VERIFICATION")
    print("=" * 50)
    
    await setup_test_users()
    await verify_role_reading()
    await verify_team_membership()
    await teardown_test_users()
    
    print("\n✅ Phase 24 RBAC Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify())
