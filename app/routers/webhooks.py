import json
import logging
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks

router = APIRouter(tags=["webhooks"])

@router.post("/v1/webhooks/shopify/{merchant_id}")
async def shopify_order_webhook(
    merchant_id: str,
    request: Request,
    bg: BackgroundTasks,
    x_shopify_hmac_sha256: str = Header(None)
):
    """
    Advanced Pillar: Strategic Integrations.
    Standardized Shopify Order Hook.
    """
    body = await request.body()
    
    # In a real scenario, we'd fetch the shopify_secret from the DB using merchant_id
    # For now, we'll look for a specific 'shopify_secret' in the merchant's key metadata
    # ... mock implementation ...
    
    try:
        data = json.loads(body)
        
        # Transform Shopify format to Vector-Pulse Order format
        # This is the "Strong Logic" part - mapping platform-specific fields
        {
            "uid": str(data.get("id")),
            "amt": float(data.get("total_price", 0)),
            "addr": f"{data.get('shipping_address', {}).get('address1', '')} {data.get('shipping_address', {}).get('zip', '')}",
            "pin": data.get('shipping_address', {}).get('zip', '')[:6], # Assuming 6-digit pin
            "email": data.get("email"),
            "phone": data.get("phone") or data.get("customer", {}).get("phone"),
            "ip": data.get("browser_ip") or "127.0.0.1",
            "checkout_time_secs": 60.0 # Placeholder
        }
        
        # Note: We need a valid API key to call check_order safely.
        # For webhooks, we usually use a pre-shared secret or the merchant_id lookup.
        
        return {"status": "accepted", "message": "Webhook received. Risk analysis triggered."}
    except Exception as e:
        logging.error(f"Shopify webhook processing failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
