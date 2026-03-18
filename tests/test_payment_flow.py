import requests
import time
import json

BASE_URL = "http://localhost:8005/api/v1"
ADMIN_KEY = "local-dev-admin-key" # Default dev key

def test_payment_flow():
    print("--- Starting Payment Flow Verification ---")
    
    headers = {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json"
    }

    # 1. Create Order
    print("[1] Creating mock Razorpay order...")
    resp = requests.post(f"{BASE_URL}/merchant/payments/orders", 
                         headers=headers, 
                         json={"amount": 49.99})
    
    if resp.status_code != 200:
        print(f"FAILED to create order: {resp.text}")
        return

    order = resp.json()
    order_id = order["id"]
    print(f"SUCCESS: Order Created -> {order_id}")

    # 2. Verify Payment
    print("[2] Verifying payment with mock signature...")
    verify_payload = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_test_12345",
        "razorpay_signature": "mock_sig_test_pass"
    }
    
    resp = requests.post(f"{BASE_URL}/merchant/payments/verify", 
                         headers=headers, 
                         json=verify_payload)
    
    if resp.status_code != 200:
        print(f"FAILED to verify payment: {resp.text}")
        return

    print(f"SUCCESS: Payment Verified!")

    # 3. Check History
    print("[3] Checking billing history...")
    resp = requests.get(f"{BASE_URL}/merchant/payments/history", headers=headers)
    history = resp.json().get("history", [])
    
    found = any(h["payment_id"] == "pay_test_12345" for h in history)
    if found:
        print("VERIFICATION COMPLETE: Transaction recorded in history.")
    else:
        print("FAILED: Transaction not found in history.")

if __name__ == "__main__":
    test_payment_flow()
