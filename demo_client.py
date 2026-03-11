import requests
import time
import random

# Use the live production URL
API_URL = "http://localhost:8000/v1/risk-check"

# The free tier API key we just generated
API_KEY = "vp_Esy2gTFjBdkHdC7kt-z6VS0TiQW1q03dX3Ni4-SKYus"
HEADERS = {"X-API-Key": API_KEY}

def simulate_orders():
    # Diversified scenarios to test different parts of your Rust/Python logic
    scenarios = [
        {"uid": "user_1", "amt": 1200, "addr": "HSR Layout, Bangalore", "pin": "560102"}, # Normal
        {"uid": "user_2", "amt": 15000, "addr": "Indore, MP", "pin": "452001"},           # Potential Price Anomaly
        {"uid": "user_3", "amt": 500, "addr": "Mumbai, MH", "pin": "400001"},             # Standard Order
        {"uid": "bot_1", "amt": 2000, "addr": "Cloud Kitchen, Delhi", "pin": "110001"},    # Sybil Attack Part 1
        {"uid": "bot_2", "amt": 2100, "addr": "Cloud Kitchen, Delhi", "pin": "110001"},    # Sybil Attack Part 2
        {"uid": "bot_3", "amt": 1900, "addr": "Cloud Kitchen, Delhi", "pin": "110001"},    # Sybil Attack Part 3
        {"uid": "bot_4", "amt": 2000, "addr": "Cloud Kitchen, Delhi", "pin": "110001"},    # Sybil Attack Part 4 (Trigger!)
    ]

    print("🚀 Vector-Pulse: Starting Live RTO Shield Simulation...")
    print(f"📡 Targeting API at: {API_URL}")
    print("-" * 50)

    while True:
        scenario = random.choice(scenarios)
        try:
            # Hit the live Render API
            response = requests.post(API_URL, json=scenario, headers=HEADERS)
            
            if response.status_code == 200:
                data = response.json()
                decision = data.get('decision', 'UNKNOWN')
                reasons = data.get('risk_factors', [])
                
                status_icon = "✅" if decision == "ALLOW_COD" else "🚨"
                reason_str = f" | Reasons: {reasons}" if reasons else ""
                
                print(f"{status_icon} User: {scenario['uid']:<8} | Decision: {decision:<13}{reason_str}")
            else:
                print(f"⚠️ Server Error: {response.status_code} | {response.text}")

        except requests.exceptions.ConnectionError:
            print("❌ API Offline: Ensure 'docker-compose up' is running.")
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
        
        # Fast simulation speed to see the monitor move
        time.sleep(1.0)

if __name__ == "__main__":
    simulate_orders()
