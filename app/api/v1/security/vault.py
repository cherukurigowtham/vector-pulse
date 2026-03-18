from fastapi import APIRouter, Depends, HTTPException
from app.services.vault_service import VaultService
from app.core.security import require_role

router = APIRouter(prefix="/security/vault", tags=["Security Vault"])

# Factory for VaultService (can be moved to a global factory later)
def get_vault_service() -> VaultService:
    return VaultService()

@router.post("/secret", summary="Store a secret in the encrypted vault.")
async def store_secret(
    secret_data: dict, 
    session: dict = Depends(require_role(["ADMIN"])),
    vault: VaultService = Depends(get_vault_service)
):
    await vault.store_secret(session["email"], secret_data["key"], secret_data["value"])
    return {"status": "secret_stored"}

@router.get("/secret/{key}", summary="Retrieve a secret from the vault.")
async def get_secret(
    key: str,
    session: dict = Depends(require_role(["ADMIN"])),
    vault: VaultService = Depends(get_vault_service)
):
    secret = await vault.get_secret(session["email"], key)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return {"key": key, "value": secret}
