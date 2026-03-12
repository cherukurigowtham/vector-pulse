import asyncio
from api_gateway import app, r, _check_velocity, _check_sybil, _check_price_anomaly, _get_trust_score
import logging

async def verify():
    print("Testing Backend Async Refactor...")
    
    # 1. Test Health
    try:
        health_status = await r.ping()
        print(f"Redis Ping: {health_status}")
    except Exception as e:
        print(f"Redis Ping Failed (Expected if local redis is off): {e}")

    # 2. Test Trust Score Fallback/Logic
    print("Testing Trust Score...")
    score = await _get_trust_score("non_existent_user")
    print(f"Trust Score (Fallback): {score}")

    # 3. Test Velocity Logic
    print("Testing Velocity...")
    is_velocity = await _check_velocity("test_user_unique")
    print(f"Velocity Flag: {is_velocity}")

    # 4. Test Price Anomaly
    print("Testing Price Anomaly...")
    anomaly, avg, std = await _check_price_anomaly("test_user_price", 1000.0)
    print(f"Anomaly: {anomaly}, Avg: {avg}")

    print("Verification Script Finished.")

if __name__ == "__main__":
    asyncio.run(verify())
