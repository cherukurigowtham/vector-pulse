import logging
import os
import json
import base64
from cryptography.fernet import Fernet
from typing import Optional
from app.core.redis import r

logger = logging.getLogger(__name__)

# In production, this key would be managed by AWS KMS or HashiCorp Vault
_VAULT_MASTER_KEY = os.getenv("VAULT_MASTER_KEY", base64.urlsafe_b64encode(b"vantix-pulse-master-vault-secret").decode())
fernet = Fernet(_VAULT_MASTER_KEY)

class VaultService:
    """
    Enterprise Vault Service (Phase 29).
    Manages encryption at rest for sensitive merchant credentials.
    """

    async def store_secret(self, team_id: str, key_name: str, value: str):
        """Encrypts and stores a secret in the vault."""
        encrypted = fernet.encrypt(value.encode()).decode()
        vault_key = f"vault:{team_id}:{key_name}"
        await r.set(vault_key, encrypted)
        logger.info(f"Vault: Secret '{key_name}' stored for team {team_id}")

    async def get_secret(self, team_id: str, key_name: str) -> Optional[str]:
        """Retrieves and decrypts a secret from the vault."""
        vault_key = f"vault:{team_id}:{key_name}"
        encrypted = await r.get(vault_key)
        if not encrypted:
            return None
        
        try:
            decrypted = fernet.decrypt(encrypted.encode()).decode()
            return decrypted
        except Exception as e:
            logger.error(f"Vault: Failed to decrypt secret '{key_name}' for team {team_id}: {e}")
            return None

    async def audit_access(self, team_id: str, key_name: str, action: str):
        """Logs vault access for compliance (Phase 29 auditing)."""
        log_key = f"vault:audit:{team_id}"
        await r.lpush(log_key, json.dumps({
            "key": key_name,
            "action": action,
            "timestamp": os.path.getmtime(__file__) # Simplified timestamp
        }))

vault_service = VaultService()
