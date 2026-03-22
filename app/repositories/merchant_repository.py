from typing import Optional, Dict, Any
from app.repositories.base_repository import BaseRepository
from app.core.redis import rk

class MerchantRepository(BaseRepository):
    """
    Handles Merchant Profile, API Key state, and Session management.
    """
    def __init__(self):
        super().__init__("Merchant")

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return await self.redis.hgetall(rk(f"user:{email}"))

    async def get_key_profile(self, key_hash: str) -> Optional[Dict[str, Any]]:
        return await self.redis.hgetall(rk(f"apikey:{key_hash}"))

    async def get_session_email(self, session_id: str) -> Optional[str]:
        return await self.redis.get(rk(f"session:{session_id}"))

    async def set_user_field(self, email: str, mapping: Dict[str, Any]):
        await self.redis.hset(rk(f"user:{email}"), mapping=mapping)

    async def get_usage(self, key_hash: str, month: str) -> int:
        val = await self.redis.get(rk(f"usage:{key_hash}:{month}"))
        return int(val or 0)
