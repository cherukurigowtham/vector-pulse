from fastapi import APIRouter, Depends, Response, Request, HTTPException
from app.core.security import verify_jwt, create_jwt_token
from app.repositories.factory import get_merchant_repo
from app.repositories.merchant_repository import MerchantRepository

router = APIRouter(prefix="/security/auth", tags=["Security Auth"])

@router.post("/login", summary="Merchant Login.")
async def login(credentials: dict, response: Response, repo: MerchantRepository = Depends(get_merchant_repo)):
    # Simplified login logic for professional refactoring
    user = await repo.get_user_by_email(credentials.get("email"))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    token = create_jwt_token({"sub": user["email"], "role": user["role"], "team_id": user["team_id"]})
    response.set_cookie(key="vp_token", value=token, httponly=True)
    return {"status": "success"}

@router.get("/me", summary="Check current auth state.")
async def get_me(request: Request):
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user
