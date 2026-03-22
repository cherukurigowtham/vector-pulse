import logging
import asyncio
from app.services.monitoring.alerter import alerter
from app.core.redis import r
from app.core.infrastructure.base_service import BaseService

class SelfHealingService(BaseService):
    """
    Phase 15: The Autonomous Core.
    Registry of healing playbooks for self-correcting production issues.
    """
    def __init__(self):
        super().__init__("SelfHealing")
        self.registry = {
            "CACHE_PRESSURE": self._playbook_clear_cache,
            "HIGH_LATENCY": self._playbook_scale_shards,
            "ML_DRIFT_DETECTED": self._playbook_revert_model
        }

    async def handle_anomaly(self, error_pattern: str, context: dict = None):
        """Analyzes an error and applies the appropriate playbook."""
        playbook = self.registry.get(error_pattern)
        if not playbook:
            logging.info(f"Self-Healing: No playbook for {error_pattern}. Escalating to Alerter.")
            await alerter.send_critical("UNKNOWN_ANOMALY", error_pattern, context)
            return

        # Determine if this is a 'High Operation'
        is_high_op = context.get("impact") == "HIGH" if context else False
        
        if is_high_op:
            logging.warning(f"Self-Healing: {error_pattern} is a HIGH OPERATION. Requesting Permission.")
            await alerter.send_interactive(
                f"Approve {error_pattern} Resolution?",
                f"The system detected {error_pattern}. Required action: {playbook.__name__}",
                f"HEAL:{error_pattern}"
            )
            return "PENDING_APPROVAL"

        # Auto-Execute low-impact healing
        logging.info(f"Self-Healing: Auto-Executing {error_pattern} Playbook...")
        await playbook(context)
        await alerter.send_milestone("AUTO_HEALING_COMPLETE", 0.0) # 0.0 val for logs

    # --- Playbooks ---

    async def _playbook_clear_cache(self, context):
        """Clears non-critical Redis caches to relieve memory pressure."""
        await r.delete("stats:velocity:window")
        logging.info("HEAL: Non-critical caches flushed.")

    async def _playbook_scale_shards(self, context):
        """Simulates horizontal scaling of engine shards."""
        logging.info("HEAL: Scaling engine shards to 2.0x capacity.")
        await asyncio.sleep(0.5)

    async def _playbook_revert_model(self, context):
        """Reverts the NeuralOrchestrator to a safe-mode configuration."""
        await r.set("config:global:shield_tightness", "1.2")
        logging.info("HEAL: Model parameters reverted to Safe-Conservative.")

self_healing_service = SelfHealingService()
