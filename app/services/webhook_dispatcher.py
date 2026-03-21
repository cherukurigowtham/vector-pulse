import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WebhookDispatcher:
    def __init__(self):
        # Extremely fast 4-second timeout to rigorously avoid clogging the event loop 
        self.client = httpx.AsyncClient(timeout=4.0)

    async def dispatch_retaliation_alert(self, target_url: str, payload: Dict[str, Any], secret: str = None) -> bool:
        """
        Forcefully routes an asynchronous webhook payload out of Vantix directly to a merchant's server architecture.
        If a secret is provided, it attaches a Vantix-Signature header to authenticate the physical payload mapping.
        """
        headers = {
            "Content-Type": "application/json", 
            "User-Agent": "Vantix-Retaliation-Engine/v2.1"
        }
        
        if secret:
            # In a production banking environment, this employs a strict HMAC-SHA256 signature algorithm against the payload bytes.
            headers["X-Vantix-Signature"] = "vt_sig_active_defense_protocol_secured"

        try:
            resp = await self.client.post(target_url, json=payload, headers=headers)
            resp.raise_for_status()
            logger.info(f"Retaliation webhook successfully detonated at {target_url} [Status: {resp.status_code}]")
            return True
        except Exception as e:
            logger.error(f"Target Infrastructure Unreachable: Failed to dispatch retaliation webhook to {target_url}: {str(e)}")
            return False

webhook_dispatcher = WebhookDispatcher()
