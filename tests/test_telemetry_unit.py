import asyncio
from app.services.telemetry_service import telemetry_service
from app.core.redis import r

async def verify_telemetry():
    print("--- Testing Usage Telemetry ---")
    team_id = "test_team_telemetry"
    
    # Simulate some scans
    await telemetry_service.record_scan(team_id, 45.2, 85.0, 70.0)
    await telemetry_service.record_scan(team_id, 32.1, 12.0, 0.0)
    await telemetry_service.record_scan(team_id, 15.5, 95.0, 70.0)
    
    # Retrieve stats
    stats = await telemetry_service.get_merchant_stats(team_id)
    print(f"Stats: {stats}")
    
    assert stats["monthly_usage"] >= 3
    assert stats["today_savings_inr"] == 140.0
    assert stats["avg_latency_ms"] > 0
    
    print("\nVerification SUCCESS: Telemetry aggregation confirmed.")

if __name__ == "__main__":
    asyncio.run(verify_telemetry())
