import logging
import asyncio
import random
import time
from typing import List, Dict, Any
from app.core.redis import r
from app.services.marketplace_service import marketplace_service, AVAILABLE_APPS

logger = logging.getLogger(__name__)

class PluginDispatcher:
    """
    Asynchronously dispatches risk analysis requests to installed 3rd-party signal providers.
    Includes Phase 18 Smart Orchestration: Health Monitoring & Circuit Breaker.
    """

    CIRCUIT_THRESHOLD = 3
    CIRCUIT_TIMEOUT = 60 # seconds

    async def dispatch_signals(self, email: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls all installed apps for a merchant and aggregates their scores.
        Bypasses providers that are currently in 'Open Circuit' state.
        Returns a dict with 'results' and 'bypassed'.
        """
        installed_ids = await marketplace_service.get_installed_apps(email)
        logger.debug(f"PluginDispatcher: Merchant {email} has installed apps: {installed_ids}")
        if not installed_ids:
            return {"results": [], "bypassed": []}

        # Find the app metadata for installed apps
        apps_to_run = [app for app in AVAILABLE_APPS if app["id"] in installed_ids]
        
        # Filter based on circuit state
        final_apps = []
        bypassed_ids = []
        for app in apps_to_run:
            if await self._is_circuit_closed(app["id"]):
                final_apps.append(app)
            else:
                logger.warning(f"CIRCUIT OPEN: Bypassing provider {app['id']} due to recent failures.")
                bypassed_ids.append(app["id"])

        # Parallel execution of external signals (simulated)
        tasks = [self._run_plugin_signal(app, order_data) for app in final_apps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors and return valid results
        valid_results = [r for r in results if isinstance(r, dict)]
        
        # Also track if any actually failed during run (despite circuit being closed)
        run_failed_ids = [app["id"] for i, app in enumerate(final_apps) if results[i] is None or isinstance(results[i], Exception)]
        
        return {
            "results": valid_results,
            "bypassed": bypassed_ids + run_failed_ids
        }

    async def _is_circuit_closed(self, app_id: str) -> bool:
        """Checks if a provider is healthy enough to call."""
        fail_key = f"plugin:health:fail:{app_id}"
        open_key = f"plugin:health:open:{app_id}"
        
        # If explicit 'open' flag exists, it's open
        if await r.get(open_key):
            return False
            
        return True

    async def _record_failure(self, app_id: str):
        """Increments failure count and opens circuit if threshold reached."""
        fail_key = f"plugin:health:fail:{app_id}"
        open_key = f"plugin:health:open:{app_id}"
        
        fails = await r.incr(fail_key)
        await r.expire(fail_key, 300) # Reset failure counter if no failures for 5 mins
        
        if fails >= self.CIRCUIT_THRESHOLD:
            logger.error(f"CIRCUIT TRIGGERED: Opening circuit for {app_id} after {fails} failures.")
            await r.setex(open_key, self.CIRCUIT_TIMEOUT, "1")
            await r.delete(fail_key)

    async def _record_success(self, app_id: str):
        """Resets failures on success."""
        await r.delete(f"plugin:health:fail:{app_id}")

    async def _run_plugin_signal(self, app: Dict[str, Any], order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates an external API call to a signal provider.
        Includes Phase 18: Success/Failure recording for health tracking.
        """
        app_id = app["id"]
        try:
            # Simulated network latency for external provider
            # Phase 18: Occasional simulated timeout or failure to test resilience
            latency = random.uniform(0.01, 0.05)
            
            # 5% chance of simulated provider failure for testing
            # Specific test trigger for reliability in automation
            if random.random() < 0.05 or order_data.get("name") == "FORCE_FAILURE":
                raise Exception(f"Simulated Provider Outage: {app_id}")
                
            await asyncio.sleep(latency) 

            # Simulated logic for different providers
            signal_score = 0.0
            flags = []
            
            if app_id == "bot_shield_pro":
                # Simulated bot detection based on user_agent presence or session age
                session_id = order_data.get("uid", "")
                if len(session_id) < 10: 
                    signal_score = 0.85
                    flags.append("BOT_SIGNATURE_DETECTED")
            elif app_id == "id_verify_plus":
                # Always returns a small baseline risk for demo
                signal_score = 0.1
            elif app_id == "geo_fencer":
                # Proxy/VPN simulation
                signal_score = 0.4
                flags.append("DATA_CENTER_IP")

            # Record success
            await self._record_success(app_id)

            return {
                "app_id": app_id,
                "name": app["name"],
                "score": signal_score * app["base_weight"],
                "raw_score": signal_score,
                "flags": flags,
                "provider": app["provider"],
                "latency_sec": latency
            }
        except Exception as e:
            logger.error(f"Plugin {app_id} failed: {e}")
            await self._record_failure(app_id)
            return None

plugin_dispatcher = PluginDispatcher()
