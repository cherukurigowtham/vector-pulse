import hashlib
import hmac
import os
import logging
from app.core.config import JWT_SECRET

logger = logging.getLogger(__name__)

# In production, this SALT would be rotated via AWS KMS/HashiCorp Vault
PII_SALT = os.getenv("PII_SALT", JWT_SECRET)

class TokenizationService:
    """
    Sovereign Tokenization Service.
    Converts toxic PII (Email, Phone, IP) into mathematically unique "Identity Shadows".
    Zero-Trust: The original data is never stored and cannot be reversed without the Salt.
    """

    @staticmethod
    def tokenize(value: str | None) -> str:
        """
        Creates a salted HMAC-SHA256 signature of a PII string.
        """
        if not value:
            return "anon_unspecified"
        
        # Normalize: lower case and strip whitespace
        normalized = value.strip().lower()
        
        # Create HMAC-SHA256 shadow
        h = hmac.new(PII_SALT.encode(), normalized.encode(), hashlib.sha256)
        return h.hexdigest()

    @staticmethod
    def tokenize_ip(ip: str) -> str:
        """
        Tokenizes IP addresses while preserving entropy.
        """
        return TokenizationService.tokenize(ip)

    @staticmethod
    def anonymize_email(email: str | None) -> str:
        """
        Creates a 'safe' display version of an email for logs (e.g. g***@gmail.com)
        alongside the tokenized version.
        """
        if not email or "@" not in email:
            return "anon@vantix.ai"
        
        prefix, domain = email.split("@")
        if len(prefix) <= 2:
            return f"{prefix}***@{domain}"
        return f"{prefix[0]}***{prefix[-1]}@{domain}"

token_service = TokenizationService()
