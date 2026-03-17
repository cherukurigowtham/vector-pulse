import hmac
import hashlib
import json
import logging
import time
import httpx
from app.core.redis import r

async def dispatch_alert(merchant_email: str, alert_type: str, data: dict):
    """
    Asynchronously dispatches a signed webhook alert to the merchant's endpoint.
    Alert Types: ATTACK_WAVE_DETECTED, GLOBAL_QUARANTINE_TRIGGERED, ANOMALY_DETECTED
    """
    try:
        # 1. Fetch merchant webhook settings
        user_key = f"user:{merchant_email}"
        user_data = await r.hgetall(user_key)
        
        webhook_url = user_data.get("alert_webhook_url")
        webhook_secret = user_data.get("webhook_secret")
        
        if not webhook_url or not webhook_secret:
            return # Webhooks not configured for this merchant
        
        # 2. Prepare Payload
        payload = {
            "version": "1.0",
            "merchant": merchant_email,
            "alert_type": alert_type,
            "timestamp": time.time(),
            "data": data
        }
        payload_str = json.dumps(payload, sort_keys=True)
        
        # 3. Sign Payload
        signature = hmac.new(
            webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # 4. Dispatch (Fire and Forget/Retry)
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Content-Type": "application/json",
                "X-Vector-Pulse-Signature": signature,
                "User-Agent": "Vector-Pulse-Alert-Engine/1.0"
            }
            
            # Simple retry logic (max 3 attempts)
            for attempt in range(3):
                try:
                    response = await client.post(webhook_url, content=payload_str, headers=headers)
                    if response.status_code < 300:
                        logging.info(f"Alert {alert_type} delivered to {merchant_email} (Attempt {attempt+1})")
                        return True
                except Exception as e:
                    logging.warning(f"Webhook delivery attempt {attempt+1} failed for {merchant_email}: {e}")
                    await asyncio.sleep(1 * (attempt + 1))
        
        logging.error(f"Failed to deliver {alert_type} to {merchant_email} after 3 attempts.")
        return False
    except Exception as e:
        logging.error(f"Error in webhook dispatcher: {e}")
        return False

import asyncio # Needed for sleep in retry logic
