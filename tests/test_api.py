import unittest
import json
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.core.config import ADMIN_KEY

class TestVectorPulseAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_public_signup_ratelimit(self):
        # We can't easily test real Redis-based ratelimits without a real Redis
        # or properly patch the Redis client. 
        # For now, we'll verify the endpoint exists and handles invalid data.
        response = self.client.post("/auth/signup", json={"email": "bad", "password": "short"})
        self.assertEqual(response.status_code, 422) # Validation error from Pydantic

    @patch("app.routers.public.r")
    @patch("app.routers.public._sliding_window_rate_limit")
    def test_register_api_key_unauthorized(self, mock_limit, mock_redis):
        mock_limit.return_value = False
        response = self.client.post(
            "/v1/register", 
            json={"email": "test@example.com", "plan": "starter", "admin_key": "wrong"}
        )
        self.assertEqual(response.status_code, 403)

    @patch("app.routers.public._sliding_window_rate_limit")
    @patch("app.routers.public.r.pipeline")
    def test_register_api_key_success(self, mock_pipe_ctx, mock_limit):
        mock_limit.return_value = False
        mock_pipe = AsyncMock()
        mock_pipe_ctx.return_value.__aenter__.return_value = mock_pipe
        
        response = self.client.post(
            "/v1/register", 
            json={"email": "test@example.com", "plan": "starter", "admin_key": ADMIN_KEY}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("api_key", response.json())
        self.assertEqual(response.json()["plan"], "starter")

    @patch("app.routers.risk.r")
    @patch("app.routers.risk._sliding_window_rate_limit")
    @patch("app.routers.risk.run_risk_analysis", new_callable=AsyncMock)
    def test_risk_check_success(self, mock_analysis, mock_limit, mock_redis):
        # Mock API Key dependency
        with patch("app.core.security.r.hgetall", new_callable=AsyncMock) as mock_hget:
            mock_hget.return_value = {
                "key_hash": "mock_hash",
                "email": "merchant@example.com",
                "plan": "starter"
            }
            # Mock rate limit
            mock_limit.return_value = False
            # Mock Redis for quota
            mock_redis.get = AsyncMock(return_value=b"10")
            
            # Mock Pipeline for Background Task
            mock_pipe = AsyncMock()
            mock_redis.pipeline.return_value.__aenter__.return_value = mock_pipe
            
            # Mock Analysis result
            mock_analysis.return_value = {
                "score": 15.2,
                "flags": [],
                "metrics": {},
                "trust_score": 85.0
            }
            
            response = self.client.post(
                "/v1/risk-check",
                headers={"X-API-Key": "vp_test_key"},
                json={
                    "uid": "user_123",
                    "amt": 1500,
                    "addr": "Bangalore",
                    "pin": "560102",
                    "ip": "1.1.1.1"
                }
            )
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["decision"], "ALLOW_COD")
            self.assertEqual(response.json()["risk_score"], 15.2)

if __name__ == "__main__":
    unittest.main()
