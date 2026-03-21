import json
import logging
from app.core.redis import r

logger = logging.getLogger(__name__)

class ConsortiumRing:
    GLOBAL_CHANNEL = "vantix:global:threats"
    
    @staticmethod
    def broadcast_threat(merchant_id: str, vector_type: str, vector_hash: str, confidence: float):
        """
        Irreversibly broadcast a hashed threat vector to all connected Vantix edge-nodes globally.
        """
        try:
            payload = {
                "source_merchant": merchant_id,
                "vector_type": vector_type,  
                "vector_hash": vector_hash,  
                "confidence": confidence,
                "action": "QUARANTINED"
            }
            # Fire-and-forget publish to the global ring
            r.publish(ConsortiumRing.GLOBAL_CHANNEL, json.dumps(payload))
            logger.info(f"[CONSORTIUM] Successfully broadcasted {vector_type} threat globally.")
        except Exception as e:
            logger.error(f"[CONSORTIUM] Failed to broadcast payload: {e}")

    @staticmethod
    def _message_handler(message):
        """
        Strict synchronous handler executed by the redis-py background thread.
        Injects foreign threats directly into the local RAM Immune System cache.
        """
        try:
            if message["type"] == "message":
                payload = json.loads(message["data"])
                v_type = payload.get("vector_type")
                v_hash = payload.get("vector_hash")
                
                if v_hash and v_type:
                    # Inject into the local High-Velocity Edge RAM Cache for 2 hours (7200s)
                    cache_key = f"vantix:immune_system:{v_type}:{v_hash}"
                    # Use setex to atomically set key and TTL
                    r.setex(cache_key, 7200, "1")
                    logger.warning(f"[CONSORTIUM] Immune System Synchronized. Intercepted global threat: {v_type}")
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
