import json
import logging
from typing import List, Dict, Any
from app.core.redis import r

logger = logging.getLogger(__name__)

# Registry of available Signal Providers (Phase 17 Marketplace)
AVAILABLE_APPS = [
    {
        "id": "bot_shield_pro",
        "name": "Bot-Shield Pro",
        "provider": "Vantix Labs",
        "description": "Advanced L7 bot detection with behavioral fingerprinting.",
        "icon": "🛡️",
        "category": "Security",
        "base_weight": 0.25,
        "price": "Free (Beta)"
    },
    {
        "id": "id_verify_plus",
        "name": "ID-Verify Plus",
        "provider": "CivicTrust",
        "description": "Real-time government ID and biometric verification.",
        "icon": "🆔",
        "category": "Identity",
        "base_weight": 0.40,
        "price": "$0.50/check"
    },
    {
        "id": "geo_fencer",
        "name": "Precision Geo-Fencer",
        "provider": "MapSafe",
        "description": "Hyper-accurate proxy and VPN detection using carrier-grade data.",
        "icon": "📍",
        "category": "Infrastructure",
        "base_weight": 0.15,
        "price": "Premium"
    }
]

class MarketplaceService:
    """
    Manages the installation and logic of 3rd-party Signal Providers.
    """
    
    _INSTALLED_APPS_KEY = "merchant:{email}:apps"
    _APP_POLICY_KEY = "merchant:{email}:app:policy:{app_id}"

    async def list_available_apps(self) -> List[Dict[str, Any]]:
        return AVAILABLE_APPS

    async def get_installed_apps(self, email: str) -> List[str]:
        """Returns list of app IDs installed by this merchant."""
        apps = await r.smembers(self._INSTALLED_APPS_KEY.format(email=email))
        return list(apps)

    async def get_app_failure_policy(self, email: str, app_id: str) -> str:
        """Returns the failure policy for an app (default: FAIL_OPEN)."""
        policy = await r.get(self._APP_POLICY_KEY.format(email=email, app_id=app_id))
        return policy or "FAIL_OPEN"

    async def set_app_failure_policy(self, email: str, app_id: str, policy: str):
        """Sets the failure policy (FAIL_OPEN, FAIL_CLOSED, SUBSTITUTE_INTERNAL)."""
        valid_policies = ["FAIL_OPEN", "FAIL_CLOSED", "SUBSTITUTE_INTERNAL"]
        if policy not in valid_policies:
            raise ValueError(f"Invalid policy: {policy}")
        await r.set(self._APP_POLICY_KEY.format(email=email, app_id=app_id), policy)

    async def install_app(self, email: str, app_id: str):
        if not any(app["id"] == app_id for app in AVAILABLE_APPS):
            raise ValueError(f"App {app_id} not found in marketplace")
        await r.sadd(self._INSTALLED_APPS_KEY.format(email=email), app_id)
        # Default policy is FAIL_OPEN for new installs
        await self.set_app_failure_policy(email, app_id, "FAIL_OPEN")
        logger.info(f"Merchant {email} installed marketplace app {app_id}")

    async def uninstall_app(self, email: str, app_id: str):
        await r.srem(self._INSTALLED_APPS_KEY.format(email=email), app_id)
        await r.delete(self._APP_POLICY_KEY.format(email=email, app_id=app_id))
        logger.info(f"Merchant {email} uninstalled marketplace app {app_id}")

marketplace_service = MarketplaceService()
