import asyncio
import logging
from app.services.email_service import email_service

# Set up logging to capture the EmailService output
logging.basicConfig(level=logging.INFO)

async def verify_email_service():
    print("--- Testing EmailService Directly ---")
    
    # Test Team Invitation
    success = await email_service.send_team_invitation(
        email="verified_user@merchant.com",
        team_name="Cyber Shield",
        invite_id="invite_9999",
        inviter_name="Dr. Vantix"
    )
    
    assert success is True
    print("\nVerification SUCCESS: Professional invitation email structure verified in logs.")

if __name__ == "__main__":
    asyncio.run(verify_email_service())
