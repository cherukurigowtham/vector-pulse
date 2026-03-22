import json
import logging
from app.core.redis import r

logger = logging.getLogger(__name__)

class ConsortiumRing:
    GLOBAL_CHANNEL = "vantix:global:threats"
    
    @staticmethod
    def broadcast_threat(merchant_id: str, vector_type: str, vector_hash: str, confidence: float):
        """
        Irreversibly broadcast a hashed threat vector.
        """
        ConsortiumRing._publish("THR", merchant_id, vector_type, vector_hash, confidence)

    @staticmethod
    def broadcast_trust(merchant_id: str, vector_type: str, vector_hash: str):
        """
        Broadcast a 'Trust Commitment'. Triggered on successful transaction outcomes.
        This build the global 'Identity Aura' for the $100B valuation.
        """
        ConsortiumRing._publish("TRU", merchant_id, vector_type, vector_hash, 1.0)

    @staticmethod
    def _publish(action: str, merchant_id: str, vector_type: str, vector_hash: str, confidence: float):
        try:
            payload = {
                "action": action, # THR (Threat) or TRU (Trust)
                "merchant": merchant_id,
                "v_type": vector_type,  
                "v_hash": vector_hash,  
                "conf": confidence
            }
            r.publish(ConsortiumRing.GLOBAL_CHANNEL, json.dumps(payload))
            logger.info(f"[CONSORTIUM] {action} broadcasted for {vector_type} globally.")
        except Exception as e:
            logger.error(f"[CONSORTIUM] Publish failed: {e}")

    @staticmethod
    def _message_handler(message):
        """
        Strict synchronous handler executed by the redis-py background thread.
        Injects foreign threats directly into the local RAM Immune System cache.
        """
        try:
            if message["type"] == "message":
                payload = json.loads(message["data"])
                v_type = payload.get("v_type")
                v_hash = payload.get("v_hash")
                action = payload.get("action", "THR")
                
                if v_hash and v_type:
                    if action == "THR":
                        # Negative Signal: Inject into local block-cache (2 hours)
                        cache_key = f"vantix:immune_system:{v_type}:{v_hash}"
                        r.setex(cache_key, 7200, "1")
                        logger.warning(f"[CONSORTIUM] Intercepted global threat: {v_type}")
                    elif action == "TRU":
                        # Positive Signal: 'Identity Aura' Accumulation (24 hours)
                        # We use a global HyperLogLog to track trust units for $100B scale
                        aura_key = f"vantix:identity_aura:{v_type}:{v_hash}"
                        r.pfadd(aura_key, payload.get("merchant", "unknown"))
                        r.expire(aura_key, 86400)
                        logger.info(f"[CONSORTIUM] Global Trust Pulse detected for {v_type}")
        except Exception as e:
            logger.error(f"[CONSORTIUM] Handler failed: {e}")

    @staticmethod
    def attach_listener():
        """
        Spawns a native non-blocking daemon thread to subscribe to the global ring.
        """
        try:
            pubsub = r.pubsub()
            pubsub.subscribe(**{ConsortiumRing.GLOBAL_CHANNEL: ConsortiumRing._message_handler})
            logger.info(f"[CONSORTIUM] Node dynamically attached to Global Threat Ring.")
            return pubsub.run_in_thread(sleep_time=0.01, daemon=True)
        except Exception as e:
            logger.error(f"[CONSORTIUM] Failed to attach global listener: {e}")
            return None
