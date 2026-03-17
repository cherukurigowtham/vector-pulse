import httpx
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("vantix")

class VantixClient:
    """
    Official Vantix Python SDK.
    High-performance, asynchronous client for order risk analysis.
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.vantix.ai"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            timeout=5.0
        )

    async def test_connection(self) -> bool:
        """Verifies if the API key is valid."""
        try:
            resp = await self.http_client.post("/v1/auth/test-connection")
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Vantix connection failed: {e}")
            return False

    async def analyze_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends order data to Vantix for real-time risk analysis.
        
        :param order_data: Dictionary containing uid, amt, addr, pin, ip, etc.
        :return: Risk analysis result including score and recommended actions.
        """
        start_time = time.time()
        try:
            resp = await self.http_client.post("/v1/risk/analyze", json=order_data)
            resp.raise_for_status()
            result = resp.json()
            latency = (time.time() - start_time) * 1000
            logger.debug(f"Vantix analysis complete: {result.get('score')} risk in {latency:.2f}ms")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"Vantix API error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Vantix Client error: {e}")
            raise

    async def close(self):
        await self.http_client.aclose()
