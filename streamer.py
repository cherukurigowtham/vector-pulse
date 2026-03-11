import time
import random

def generate_transaction():
    """Simulates a live credit card swipe"""
    users = ["user_1", "user_2", "user_3", "user_4", "user_5"]
    return {
        "user_id": random.choice(users),
        "amount": round(random.uniform(10.0, 5000.0), 2),
        "timestamp": time.time()
    }

if __name__ == "__main__":
    print("Starting Live Stream... Press Ctrl+C to stop.")
    while True:
        tx = generate_transaction()
        print(f"Incoming: {tx}")
        time.sleep(0.1) # Simulate 10 transactions per second
