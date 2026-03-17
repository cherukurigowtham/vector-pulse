import json
import base64
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SignalTunnel:
    """
    Encrypted Telemetry Tunnel (Phase 16).
    Ensures behavioral clickstream data is decrypted securely on arrival.
    Currently implements a Base64 + Simulated XOR (Hardware-Aware) layer
    to prevent simple inspection and tampering.
    """
    
    _STATIC_OBFUSCATION_KEY = b"VANTIX_IRON_SHIELD_2026"

    def decrypt_signal(self, payload: str) -> Dict[str, Any]:
        """
        Decrypts an incoming behavioral packet.
        In production, this would use AES-GCM with rotateable keys.
        """
        try:
            # 1. Decode wrap
            raw_data = base64.b64decode(payload)
            
            # 2. XOR Decryption (Simulated Hardware-Aware Layer)
            decrypted = bytes([b ^ self._STATIC_OBFUSCATION_KEY[i % len(self._STATIC_OBFUSCATION_KEY)] 
                              for i, b in enumerate(raw_data)])
            
            # 3. JSON Parse
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            logger.error(f"Signal Tunnel Decryption Failed: {e}")
            raise ValueError("Malformed or tampered signal packet")

    def encrypt_signal(self, data: Dict[str, Any]) -> str:
        """Helper for SDK-side simulation."""
        json_str = json.dumps(data).encode('utf-8')
        encrypted = bytes([b ^ self._STATIC_OBFUSCATION_KEY[i % len(self._STATIC_OBFUSCATION_KEY)] 
                          for i, b in enumerate(json_str)])
        return base64.b64encode(encrypted).decode('utf-8')

tunnel = SignalTunnel()
