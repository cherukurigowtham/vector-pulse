import asyncio
import json
import time
import os
import sys

# Ensure app is in path
sys.path.append(os.getcwd())

from app.core.redis import r
from app.db.database import AUDIT_STORE
from app.services.autopilot_service import autopilot_service

async def verify():
    print("Preparing test data for Auto-Pilot...")
    email = "autopilot_test@vantix.com"
    
    # 1. Clear old data
    await r.delete(f"config:{email}")
    if not AUDIT_STORE.db: await AUDIT_STORE.init()
    
    # 2. Inject 'Outcome Drift' (High RTO)
    print("Injecting 50 RTO outcomes to simulate 'Outcome Drift'...")
    for i in range(50):
        # We use a direct INSERT for the test to set 'outcome' specifically
        await AUDIT_STORE.db.execute(
            "INSERT INTO risk_audit (risk_id, uid, email, risk_score, decision, shadow_mode, reasons, metrics, timestamp, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"drift_{i}", f"U_{i}", email, 45.0, "ALLOW_COD", 0, "[]", json.dumps({"vpn": False, "trust": 50}), time.time() - (i * 3600), "RTO")
        )
    await AUDIT_STORE.db.commit()

    # 3. Request Suggestion
    print("Requesting AI Optimization Suggestion...")
    suggestion = await autopilot_service.get_optimization_suggestion(email)
    print(f"Suggestion Status: {suggestion['status']}")
    
    if suggestion['status'] == 'IMPROVEMENT_AVAILABLE':
        print(f"Proposed Factor: {suggestion['suggestion']['factor']}")
        print(f"Reason: {suggestion['suggestion']['reason']}")
        
        # 4. Apply Optimization
        print("Applying AI Optimization...")
        success = await autopilot_service.apply_optimization(email, suggestion['suggestion']['candidate_config'])
        
        if success:
            # 5. Verify Redis Config Update
            config_raw = await r.get(f"config:{email}")
            config = json.loads(config_raw)
            factor = suggestion['suggestion']['factor']
            if config.get(factor) == 25.0:
                print(f"✅ Auto-Pilot Success: {factor} optimized to 25.0")
            else:
                print(f"❌ Auto-Pilot Failed: Config not updated correctly. Got {config.get(factor)}")
        else:
            print("❌ Apply Optimization Failed!")
    else:
        print(f"❌ Auto-Pilot Failed: Expected IMPROVEMENT_AVAILABLE but got {suggestion['status']}")
        print(f"Message: {suggestion.get('message')}")

if __name__ == "__main__":
    asyncio.run(verify())
