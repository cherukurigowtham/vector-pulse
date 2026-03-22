import json
import hmac
import hashlib
from app.core.redis import r
from app.core.infrastructure.base_service import BaseService

class SovereignAlerter(BaseService):
    """
    Phase 14: Solo-Dev Operations.
    Provides a high-fidelity bridge to mobile devices (Telegram/Push).
    """
    def __init__(self):
        super().__init__("SovereignAlerter")
        self.channel = "vantix:ops:mobile_alerts"

    async def send_critical(self, title: str, body: str, metadata: dict = None):
        """Dispatches a critical alert to the solo developer's mobile bridge."""
        payload = {
            "level": "CRITICAL",
            "title": f"🚨 {title}",
            "body": body,
            "ts": time.time(),
            "metadata": metadata or {},
            "urgency": "IMMEDIATE"
        }
        
        # In a real environment, this would call a Telegram/Twilio API.
        # Here, we push to a high-priority Redis queue for the Mobile Bridge daemon.
        await r.lpush(self.channel, json.dumps(payload))
        await r.ltrim(self.channel, 0, 99) # Keep recent 100 alerts
        
        logging.error(f"[SOVEREIGN_ALERT] {title}: {body}")
        return True

    async def send_milestone(self, title: str, amount: float):
        """Notification for major financial milestones."""
        payload = {
            "level": "MILESTONE",
            "title": f"💰 {title}",
            "body": f"Value Processed: Rs {amount:,.2f}",
            "ts": time.time(),
            "urgency": "LOW"
        }
        await r.lpush(self.channel, json.dumps(payload))
        logging.info(f"[SOVEREIGN_MILESTONE] {title}: {amount}")

    async def send_interactive(self, title: str, body: str, action_id: str, metadata: dict = None):
        """
        Sends an alert that requires a human's digital signature to execute.
        Used for 'High Operations' like global flushes or model rollbacks.
        """
        # Generate a one-time signature for this action
        secret = "SOVEREIGN_OPS_SECRET_V1" # In prod, from Vault
        token = hmac.new(
            secret.encode(), 
            f"{action_id}:{time.time()}".encode(), 
            hashlib.sha256
        ).hexdigest()[:12]

        payload = {
            "level": "PERMISSION_REQUIRED",
            "title": f"🛡️ {title}",
            "body": body,
            "action_id": action_id,
            "approval_token": token,
            "ts": time.time(),
            "metadata": metadata or {},
            "urgency": "CRITICAL",
            "interactive": True
        }
        
        await r.lpush(self.channel, json.dumps(payload))
        await r.setex(f"ops:pending:{token}", 3600, action_id) # 1 hour TTL for approval
        
        logging.warning(f"[SOVEREIGN_INTERACTIVE] Permission Requested: {action_id} | Token: {token}")
        return token

alerter = SovereignAlerter()
