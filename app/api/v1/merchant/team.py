from fastapi import APIRouter, Depends, HTTPException
from app.services.merchant.team_service import TeamService
from app.core.security import require_role

router = APIRouter(prefix="/merchant/team", tags=["Merchant Team"])

def get_team_service() -> TeamService:
    return TeamService()

@router.get("/members", summary="Get organization members.")
async def get_members(
    session: dict = Depends(require_role(["ADMIN", "ANALYST"])),
    service: TeamService = Depends(get_team_service)
):
    return await service.get_members(session["team_id"])

@router.post("/invite", summary="Invite a new member to the team.")
async def invite_member(
    invite_data: dict, # Simplified for example
    session: dict = Depends(require_role(["ADMIN"])),
    service: TeamService = Depends(get_team_service)
):
    invite_id = await service.invite_member(
        session["team_id"], 
        invite_data["email"], 
        invite_data["role"], 
        session["email"]
    )
    return {"status": "success", "invite_id": invite_id}
