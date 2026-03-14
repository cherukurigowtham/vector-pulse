import unittest
from fastapi.testclient import TestClient
import json
import time
import sys
from unittest.mock import MagicMock, AsyncMock

# Mock vector_pulse before it gets imported by api_gateway
mock_vp = MagicMock()
mock_vp.is_gibberish_address.return_value = False
mock_vp.is_suspicious_name.return_value = False
mock_vp.is_suspicious_phone.return_value = False
mock_vp.is_email_name_mismatch.return_value = False
mock_vp.has_poor_address_structure.return_value = False
sys.modules["vector_pulse"] = mock_vp

import api_gateway
from api_gateway import app, _hash_key, RISK_CONFIG, RATE_LIMITS

class TestMerchantEndpoints(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_email = "merchant@test.com"
        self.test_key = "vp_test_merchant_123"
        self.key_hash = _hash_key(self.test_key)
        
        # Patch api_gateway.r with an AsyncMock
        self.mock_r = AsyncMock()
        api_gateway.r = self.mock_r

    async def test_get_config_success(self):
        self.mock_r.hgetall.return_value = {
            "email": self.test_email,
            "plan": "starter",
            "risk_decision_threshold": "50"
        }
        
        response = self.client.get("/v1/merchant/config", headers={"X-API-Key": self.test_key})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], self.test_email)
        self.assertEqual(data["risk_config"]["decision_threshold"], 50)

    async def test_get_config_invalid_key(self):
        self.mock_r.hgetall.return_value = {}
        response = self.client.get("/v1/merchant/config", headers={"X-API-Key": "invalid_key"})
        self.assertEqual(response.status_code, 403)

    async def test_update_config_success(self):
        self.mock_r.hgetall.side_effect = [
            {"email": self.test_email, "plan": "starter"}, # Initial load in require_merchant_key
            {"email": self.test_email, "plan": "starter", "risk_decision_threshold": "85"} # Load after update
        ]
        
        update_data = {"decision_threshold": 85}
        response = self.client.post(
            "/v1/merchant/config", 
            headers={"X-API-Key": self.test_key},
            json=update_data
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["risk_config"]["decision_threshold"], 85)
        self.mock_r.hset.assert_called()

    async def test_get_stats_success(self):
        self.mock_r.hgetall.return_value = {
            "email": self.test_email,
            "plan": "starter"
        }
        self.mock_r.get.side_effect = [
            "150", # usage_this_month
            "10",  # total_blocks
            "5000" # total_savings
        ]
        
        response = self.client.get("/v1/merchant/stats", headers={"X-API-Key": self.test_key})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_blocks"], 10)
        self.assertEqual(data["total_savings_inr"], 5000)
        self.assertEqual(data["usage_this_month"], 150)

if __name__ == "__main__":
    unittest.main()
