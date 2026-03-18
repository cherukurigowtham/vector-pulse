import asyncio
import logging
import random
from app.models import Order
from app.api.v1.risk.analysis import scan_order
from app.services.risk.factory import get_risk_engine
from app.core.config import RISK_CONFIG

async def verify_modular_engine():
    print("--- Verifying Modular Google-Style Engine ---")
    
    # Setup test order
    order = Order(
        uid="modular_test_user",
        name="Modular Test",
        email="modular@vantix.com",
        amt=2500,
        addr="123 Modular Ave, Silicon Valley",
        ip="1.1.1.1",
        pin="110001",
        checkout_time_secs=5.0
    )
    
    # Mock merchant context
    merchant = {"email": "ceo@vantix.com", "key_hash": "test_hash"}
    
    # Get the new modular engine
    engine = get_risk_engine()
    
    print("Executing modular risk analysis...")
    result = await scan_order(order, merchant, engine)
    
    print(f"Result Score: {result['score']}")
    print(f"Result Decision: {result['decision']}")
    print(f"Active Flags: {result['flags']}")
    
    assert "score" in result
    assert "decision" in result
    assert isinstance(result["flags"], list)
    
    print("Verification SUCCESS: Modular engine operational.")

if __name__ == "__main__":
    asyncio.run(verify_modular_engine())
