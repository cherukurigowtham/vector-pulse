import time
from typing import Dict, Any
from app.core.infrastructure.base_service import BaseService
from app.repositories.merchant_repository import MerchantRepository

class UserService(BaseService):
    """
    Handles Merchant Profile and Account Lifecycle management.
    File length: <100 lines.
    """
    def __init__(self, repo: MerchantRepository):
        super().__init__("User")
        self.repo = repo

    async def get_profile(self, email: str) -> Dict[str, Any]:
        """Aggregates user data, usage, and metrics for the portal."""
        user = await self.repo.get_user_by_email(email)
        if not user:
            return {}
            
        current_month = time.strftime('%Y-%m')
        key_hash = user.get("key_hash")
        
        usage = await self.repo.get_usage(key_hash, current_month) if key_hash else 0
        
        return {
            "email": email,
            "role": user.get("role", "VIEWER"),
            "team_id": user.get("team_id"),
            "usage_this_month": usage,
            "settings": {
                "company": user.get("company_name"),
                "category": user.get("category")
            }
        }

    async def update_settings(self, email: str, settings: Dict[str, Any]):
        """Standardized update with audit logging."""
        await self.repo.set_user_field(email, settings)
        self.log_event("settings_updated", email=email, fields=list(settings.keys()))
