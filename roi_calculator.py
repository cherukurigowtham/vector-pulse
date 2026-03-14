import csv
import json
import asyncio
import aiohttp
import sys

# Vector Pulse ROI Calculator
# This script helps merchants simulate savings by running historical order data through the Vector Pulse API.

API_URL = "https://vector-pulse-b97i.onrender.com/v1/risk-check"
API_KEY = "YOUR_API_KEY"

async def check_order(session, order_data):
    headers = {"X-API-Key": API_KEY}
    try:
        async with session.post(API_URL, json=order_data, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"error": f"HTTP {response.status}"}
    except Exception as e:
        return {"error": str(e)}

async def run_simulation(csv_path, savings_per_rto=100):
    print(f"--- Vector Pulse ROI Simulation ---")
    print(f"Loading orders from: {csv_path}")
    
    orders = []
    with open(csv_path, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Map CSV columns to Vector Pulse order model
            orders.append({
                "uid": row.get("order_id"),
                "amt": float(row.get("amount", 0)),
                "addr": row.get("address", ""),
                "pin": row.get("pincode", ""),
                "name": row.get("customer_name", ""),
                "email": row.get("customer_email", ""),
                "phone": row.get("customer_phone", ""),
                "ip": row.get("ip_address", "127.0.0.1"),
                "shadow": True # Simulation mode
            })

    print(f"Processing {len(orders)} orders...")
    
    total_blocked = 0
    total_savings = 0
    reasons_count = {}

    async with aiohttp.ClientSession() as session:
        tasks = [check_order(session, order) for order in orders]
        results = await asyncio.gather(*tasks)

    for res in results:
        if res.get("decision") == "FORCE_PREPAID":
            total_blocked += 1
            total_savings += savings_per_rto
            for factor in res.get("risk_factors", []):
                reasons_count[factor] = reasons_count.get(factor, 0) + 1

    print("\n--- Simulation Results ---")
    print(f"Total Orders Scanned: {len(orders)}")
    print(f"Fraudulent Orders Identified: {total_blocked}")
    print(f"Detection Rate: {(total_blocked / len(orders)) * 100:.2f}%")
    print(f"Projected Savings (at ₹{savings_per_rto}/RTO): ₹{total_savings}")
    
    print("\nTop Risk Factors Detected:")
    for reason, count in sorted(reasons_count.items(), key=lambda x: x[1], reverse=True):
        print(f"- {reason}: {count}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 roi_calculator.py path_to_orders.csv")
    else:
        asyncio.run(run_simulation(sys.argv[1]))
