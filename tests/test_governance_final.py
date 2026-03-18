import asyncio
import json
import os
import random
from unittest.mock import patch
from app.services.risk_service import run_risk_analysis
from app.services.governance_service import governance_service
from app.services.vault_service import vault_service
from app.models import Order
from app.db.database import AUDIT_STORE

async def verify_governance():
    print("--- Testing Phase 29: Platform Governance ---")
    await AUDIT_STORE.init()
    merchant_email = f"gov_test_{random.randint(1,1000)}@vantix.ai"
    
    uid = f"gov_user_{random.randint(1000, 9999)}"
    rand_ip = f"{random.randint(10, 200)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
    rand_email = f"user_{random.randint(1, 10000)}@governance-test.com"
    
    order = Order(
        uid=uid,
        amt=5000,
        email=rand_email,
        addr=f"{random.randint(1,9999)} Random Blvd, TestCity",
        ip=rand_ip,
        pin="560001",
        phone="9876543210", # Valid format
        checkout_time_secs=0.1, # Trigger BOT_SPEED flag
    )

    # Mock all global pulse signals that saturate the score
    with patch("app.services.risk_service.link_identity") as mock_link, \
         patch("app.services.risk_service._check_ip_intelligence") as mock_ip, \
         patch("app.services.risk_service._check_global_velocity") as mock_g_vel, \
         patch("app.services.risk_service._check_global_sybil") as mock_g_sybil:
        
        mock_link.return_value = {"hits": 0, "reputation": {}}
        mock_ip.return_value = False
        mock_g_vel.return_value = False
        mock_g_sybil.return_value = False

        # 1. Baseline Run
        res1 = await run_risk_analysis(order, None, merchant_email)
        score1 = res1["score"]
        print(f"Initial Score: {score1}")
        print(f"Initial Impacts: {res1.get('xai_impacts')}")

        # 2. Record FALSE_POSITIVE feedback
        print("Recording FALSE_POSITIVE feedback...")
        await governance_service.record_feedback(merchant_email, "risk_123", "FALSE_POSITIVE")

        # 3. Second Run (Weights should be lower)
        res2 = await run_risk_analysis(order, None, merchant_email)
        score2 = res2["score"]
        print(f"Post-Governance Score: {score2}")
        print(f"Final Impacts: {res2.get('xai_impacts')}")
        
        assert score2 < score1
        print("Verification SUCCESS: Dynamic weight reduction confirmed.")

    # 4. Vault Test
    print("\n--- Testing Vault ---")
    team_id = f"team_vault_{random.randint(1,1000)}"
    await vault_service.store_secret(team_id, "STRIPE_KEY", "sk_test_51Mz")
    secret = await vault_service.get_secret(team_id, "STRIPE_KEY")
    assert secret == "sk_test_51Mz"
    print("Vault SUCCESS: Encryption/Decryption verified.")

if __name__ == "__main__":
    asyncio.run(verify_governance())
