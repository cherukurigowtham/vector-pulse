from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_api_key
from app.services.marketplace_service import marketplace_service

router = APIRouter(tags=["marketplace"])

@router.get("/v1/marketplace/apps", summary="List all available Vantix Marketplace apps")
async def list_apps(key_data: dict = Depends(require_api_key)):
    available = await marketplace_service.list_available_apps()
    merchant_email = key_data["email"]
    installed = await marketplace_service.get_installed_apps(merchant_email)
    
    # Enrich availability with installation status and Phase 18 failure policies
    apps = []
    for app in available:
        a = app.copy()
        is_inst = app["id"] in installed
        a["is_installed"] = is_inst
        if is_inst:
            a["failure_policy"] = await marketplace_service.get_app_failure_policy(merchant_email, app["id"])
        apps.append(a)
        
    return {"apps": apps}

@router.post("/v1/marketplace/policy/{app_id}", summary="Set failure policy for an app")
async def set_policy(app_id: str, policy: str, key_data: dict = Depends(require_api_key)):
    try:
        await marketplace_service.set_app_failure_policy(key_data["email"], app_id, policy)
        return {"status": "success", "message": f"Policy for {app_id} updated to {policy}"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/v1/marketplace/install/{app_id}", summary="Install a marketplace app")
async def install_app(app_id: str, key_data: dict = Depends(require_api_key)):
    try:
        await marketplace_service.install_app(key_data["email"], app_id)
        return {"status": "success", "message": f"App {app_id} installed successfully"}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.delete("/v1/marketplace/uninstall/{app_id}", summary="Uninstall a marketplace app")
async def uninstall_app(app_id: str, key_data: dict = Depends(require_api_key)):
    await marketplace_service.uninstall_app(key_data["email"], app_id)
    return {"status": "success", "message": f"App {app_id} uninstalled"}
