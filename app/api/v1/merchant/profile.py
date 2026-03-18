from fastapi import APIRouter, Depends, Request, HTTPException
from app.services.merchant.user_service import UserService
from app.repositories.factory import get_merchant_repo
from app.core.security import require_role

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
