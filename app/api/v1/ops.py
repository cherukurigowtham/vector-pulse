import logging
from fastapi import APIRouter, HTTPException, Depends
from app.services.monitoring.alerter import alerter
from app.services.monitoring.self_healing_service import self_healing_service
from app.core.redis import r
from app.core.security import require_api_key_or_admin

router = APIRouter(tags=["ops"])

@router.post("/v1/ops/approve", summary="Authorize a High-Impact Autonomous Operation")
async def approve_operation(token: str, admin: dict = Depends(require_api_key_or_admin)):
    """
    Validates a Sovereign Permission token and executes the pending healing action.
    This is the digital signature bridge for the solo developer.
    """
    try:
        # 1. Check if token exists and is valid (1-hour TTL already handled by Redis)
        action_id = await r.get(f"ops:pending:{token}")
        if not action_id:
            raise HTTPException(status_code=404, detail="Permission token expired or invalid.")

        # 2. Execute the healing playbook
        # action_id format: "HEAL:PATTERN_NAME"
        if action_id.startswith("HEAL:"):
            pattern = action_id.split(":")[1]
            logging.warning(f"SOVEREIGN_OPS: Executing AUTHORIZED Healing for {pattern}")
            
            # Use the registry directly (Simplified for solo-ops)
            playbook = self_healing_service.registry.get(pattern)
            if playbook:
                await playbook({}) # Context empty for now
                await r.delete(f"ops:pending:{token}")
                
                await alerter.send_milestone("Sovereign Operation Executed", 0.0)
                return {"status": "success", "action": action_id, "result": "HEALING_APPLIED"}

        raise HTTPException(status_code=400, detail="Malformed action identifier.")

    except Exception as e:
        logging.error(f"Sovereign Approval Router Error: {e}")
        raise HTTPException(status_code=500, detail="Operations engine failure.")
