import asyncio
import logging
from app.routers.merchant import invite_member
from app.db.database import AUDIT_STORE

# Set up logging to capture the EmailService output
logging.basicConfig(level=logging.INFO)

async def verify_invitation_flow():
    await AUDIT_STORE.init()
    
    # Mock session for ADMIN
    mock_session = {
        "email": "owner@merchant.com",
        "role": "ADMIN",
        "team_id": "team_alpha"
    }
    
    print("--- Testing Profressional Invitation Flow ---")
    try:
        # Create team first if not exists (SQLite)
        await AUDIT_STORE.create_team("team_alpha", "Alpha Corp", "owner@merchant.com")
    except:
        pass

    try:
        # Trigger invitation
        result = await invite_member(
            email="new_joiner@example.com",
            role="ANALYST",
            session=mock_session
        )
        
        print(f"Invitation Result: {result}")
        assert result["status"] == "success"
        assert "invite_id" in result
        
        print("\nVerification SUCCESS: Professional invitation dispatched via EmailService.")
        
    finally:
        await AUDIT_STORE.close()

if __name__ == "__main__":
    asyncio.run(verify_invitation_flow())
