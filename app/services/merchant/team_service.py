from typing import List, Dict, Any
from app.core.infrastructure.base_service import BaseService
from app.db.database import AUDIT_STORE

class TeamService(BaseService):
    """
    Handles Organization-level Team management and invitations.
    """
    def __init__(self):
        super().__init__("Team")

    async def get_members(self, team_id: str) -> List[Dict[str, Any]]:
        """Retrieves all members of a specific merchant team."""
        return await AUDIT_STORE.get_team_members(team_id)

    async def invite_member(self, team_id: str, email: str, role: str, inviter: str):
        """Creates a team invitation and triggers a notification."""
        invite_id = await AUDIT_STORE.create_invitation(team_id, email, role, inviter)
        self.log_event("invite_sent", team_id=team_id, recipient=email, role=role)
        return invite_id

    async def get_invites(self, team_id: str) -> List[Dict[str, Any]]:
        return await AUDIT_STORE.get_team_invitations(team_id)
