from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict
from app.core.redis import r
import logging

class BaseRepository(ABC):
    """
    Standardizes data access across Redis, SQL, and external APIs.
    """
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"vantix.repo.{name}")
        self.redis = r

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Utility for JSON-based Redis retrieval."""
        import json
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set_json(self, key: str, data: Dict[str, Any], expire: int = 3600):
        """Utility for JSON-based Redis storage."""
        import json
        await self.redis.setex(key, expire, json.dumps(data))
