import asyncio
import json
from app.services.forensics_service import forensics_service
from app.db.database import AUDIT_STORE

async def verify_forensics():
    await AUDIT_STORE.init()
    
    # Check if we have any audit records
    team_id = "test_team"
    try:
        # Create a mock audit record if none exists
        risk_id = "test_risk_123"
        payload = {
            "risk_id": risk_id,
            "uid": "user_456",
            "email": "test@example.com",
            "team_id": team_id,
            "risk_score": 85.5,
            "decision": "BLOCK",
            "shadow_mode": 0,
            "reasons": "IMPOSSIBLE_TRAVEL,BOT_SPEED_CHECKOUT",
            "metrics": json.dumps({"lat": 12.9, "lon": 77.5}),
            "timestamp": 1679000000.0,
        }
        await AUDIT_STORE.insert_risk_audit(payload)
        
        print(f"--- Testing Forensics for {risk_id} ---")
        analysis = await forensics_service.analyze_decision(risk_id, "test@merchant.com")
        
        print("Adjudication Narrative:")
        print(analysis["adjudication_narrative"])
        print("\nForensic Signals:")
        print(json.dumps(analysis["forensic_signals"], indent=2))
        
        assert "justified" in analysis["adjudication_narrative"].lower() or "investigation" in analysis["adjudication_narrative"].lower()
        print("\nVerification SUCCESS: Forensics providing valid insights (Fallback or AI).")
        
    finally:
        await AUDIT_STORE.close()

if __name__ == "__main__":
    asyncio.run(verify_forensics())
