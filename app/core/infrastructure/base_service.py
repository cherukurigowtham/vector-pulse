import logging
import time

class BaseService:
    """
    Google-Style BaseService.
    Provides unified logging, telemetry hooks, and standard error handling logic.
    """
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"vantix.{service_name}")

    def log_event(self, event_name: str, **kwargs):
        """Standardized event logging for audit and telemetry."""
        context = {
            "service": self.service_name,
            "event": event_name,
            "timestamp": time.time(),
            **kwargs
        }
        self.logger.info(f"Event: {event_name} | Context: {context}")

    async def execute_with_telemetry(self, operation_name: str, func, *args, **kwargs):
        """Wraps execution with latency tracking and error handling."""
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000
            self.log_event(f"{operation_name}_success", duration_ms=round(duration, 2))
            return result
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self.logger.error(f"Operation {operation_name} failed: {e}", exc_info=True)
            self.log_event(f"{operation_name}_failure", error=str(e), duration_ms=round(duration, 2))
            raise
