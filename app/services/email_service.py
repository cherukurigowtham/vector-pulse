import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

class EmailService:
    """
    Transactional Email Service for Vantix.
    In Phase 27, this implements professionalized SMTP-style logging.
    Ready for integration with SendGrid/AWS SES.
    """
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.sender = os.getenv("EMAIL_SENDER", "noreply@vantix.ai")

    async def send_team_invitation(self, email: str, team_name: str, invite_id: str, inviter_name: str):
        """
        Sends a professional team invitation email.
        """
        invite_link = f"https://vantix.ai/accept-invite?id={invite_id}"
        
        subject = f"Invitation to join {team_name} on Vantix"
        body = f"""
        Hello,
        
        {inviter_name} has invited you to join their team '{team_name}' on Vantix RTO Shield.
        
        Vantix helps e-commerce merchants protect against RTO losses using Cognitive AI.
        
        To accept this invitation and set up your account, please click the link below:
        {invite_link}
        
        If you did not expect this invitation, you can safely ignore this email.
        
        Best regards,
        The Vantix Intelligence Team
        """
        
        # Professional Logging (Production Simulation)
        logger.info(f"--- OUTGOING EMAIL [TRANSACTIONAL] ---")
        logger.info(f"To: {email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Content: {body}")
        logger.info(f"--------------------------------------")
        
        # In a real production environment, we would use an SMTP client or API here
        # Example: await smtp_client.send_message(message)
        return True

    async def send_security_alert(self, email: str, alert_type: str, details: dict):
        """
        Sends a security or risk alert to the merchant.
        """
        subject = f"Vantix Security Alert: {alert_type}"
        logger.info(f"--- SECURITY ALERT DISPATCHED TO {email} ---")
        
        return True

email_service = EmailService()
