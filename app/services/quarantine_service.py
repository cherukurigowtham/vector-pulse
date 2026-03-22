import logging
from app.core.redis import r

async def process_fraud_feedback(order_hash: str, merchant_email: str):
    """
    Advanced Pillar: Autonomous Global Quarantine.
    Tracks fraud reports for a specific semantic cluster.
    If multiple merchants report fraud, the cluster is quarantined globally.
    """
    try:
        report_set = f"quarantine:reports:{order_hash}"
        # Track UNIQUE merchants reporting this cluster
        await r.sadd(report_set, merchant_email)
        await r.expire(report_set, 86400 * 7) # Keep reports for 7 days
        
        count = await r.scard(report_set)
        
        # Threshold: If 3 or more merchants report the same cluster
        if count >= 3:
            await r.sadd("global:quarantine", order_hash)
            await r.expire("global:quarantine", 86400 * 30)
            logging.warning(f"GLOBAL QUARANTINE TRIGGERED for cluster {order_hash} (Reports: {count})")
            return True
        return False
    except Exception as e:
        logging.error(f"Quarantine processing failed: {e}")
        return False

async def get_quarantine_stats():
    """Returns the size of the global quarantine list."""
    try:
        return await r.scard("global:quarantine")
    except:
        return 0
