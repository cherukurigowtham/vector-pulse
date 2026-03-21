from fastapi import APIRouter, Depends, Request, HTTPException
from app.services.merchant.user_service import UserService
from app.repositories.factory import get_merchant_repo
from app.core.security import require_role
from pydantic import BaseModel
from app.core.redis import r

router = APIRouter(prefix="/merchant/profile", tags=["Merchant Profile"])

# Internal dependency for UserService
def get_user_service() -> UserService:
    return UserService(get_merchant_repo())

@router.get("/me", summary="Get current merchant profile.")
async def get_my_profile(
    request: Request,
    service: UserService = Depends(get_user_service)
):
    email = request.state.user.get("email") if hasattr(request.state, "user") and request.state.user else None
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    return await service.get_profile(email)

@router.post("/settings", summary="Update merchant account settings.")
async def update_settings(
    settings: dict,
    session: dict = Depends(require_role(["ADMIN"])),
    service: UserService = Depends(get_user_service)
):
    await service.update_settings(session["email"], settings)
    return {"status": "success"}

class WebhookConfig(BaseModel):
    alert_webhook_url: str = ""
    webhook_secret: str = ""

@router.patch("/webhooks", summary="Configure Autonomous Retaliation Hooks")
async def update_webhooks(
    config: WebhookConfig,
    session: dict = Depends(require_role(["ADMIN"]))
):
    account_id = session.get("sub", "mc_01")
    if config.alert_webhook_url:
        r.hset(f"merchant:{account_id}:config", "alert_webhook_url", config.alert_webhook_url)
    if config.webhook_secret:
        r.hset(f"merchant:{account_id}:config", "webhook_secret", config.webhook_secret)
    return {"status": "success", "message": "Webhook engine armed."}

@router.get("/webhooks", summary="Get webhook config")
async def get_webhooks(session: dict = Depends(require_role(["ADMIN"]))):
    account_id = session.get("sub", "mc_01")
    url = r.hget(f"merchant:{account_id}:config", "alert_webhook_url")
    secret = r.hget(f"merchant:{account_id}:config", "webhook_secret")
    return {
       "alert_webhook_url": url.decode('utf-8') if url else "",
       "webhook_secret": secret.decode('utf-8') if secret else ""
    }
