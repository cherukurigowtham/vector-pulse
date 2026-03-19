import asyncio
import logging
import time
from app.models import Order
from app.models.dto.risk_context import RiskContext
from app.services.risk.factory import get_risk_engine
from app.services.risk.shield_monitor import shield_monitor
from app.services.governance_service import governance_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Simulation")

async def simulate_attack_wave():
    """
    Simulates a high-volume attack wave to trigger Shield Mode.
    """
    logger.info("Starting Attack Wave Simulation...")
    
    # 1. Clear previous logs for clean test
    from app.core.redis import r, rk
    await r.delete(rk("shield:event_log"))
    await r.delete(rk("shield:block_log"))
    
    engine = get_risk_engine()
    
    # Simulate 15 requests, 100% blocked
    for i in range(15):
        # We simulate a "Blocked" event by manually recording to the monitor
        await shield_monitor.record_decision(is_blocked=True)
        
    is_active = await shield_monitor.is_shield_active()
    logger.info(f"Shield Mode Active? {is_active}")
    
    if is_active:
        logger.info("PASSED: Shield Mode activated after attack wave.")
    else:
        logger.error("FAILED: Shield Mode did not activate.")
        return False
        
    # 2. Verify threshold tightening in Orchestrator
    order = Order(uid="attacker_1", amt=5000, addr="Indore", ip="1.2.3.4", name="Fraud Bot", pin="452001")
    context = RiskContext(order=order, merchant_email="ceo@vantix.ai")
    
    from app.core.config import RISK_CONFIG
    test_config = {**RISK_CONFIG, "velocity_weight": 40.0, "decision_threshold": 50.0}
    res = await engine.analyze(context, test_config)
    logger.info(f"Analysis result under Shield: {res['decision']} (Flags: {res['flags']})")
    
    if "SHIELD_MODE_ACTIVE" in res["flags"]:
        logger.info("PASSED: Shield Mode flag present in risk results.")
    else:
        logger.error("FAILED: Shield Mode flag missing.")
        return False
        
    return True

if __name__ == "__main__":
    asyncio.run(simulate_attack_wave())
