"""
Structured JSON Logger — Production Observability
==================================================
Every log line emits clean JSON with a consistent schema:
  { timestamp, level, service, request_id, message, ...extras }

This makes logs queryable in any aggregator: Render Logs, Datadog, CloudWatch, Grafana Loki.
"""
import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(service_name: str = "vantix-api") -> None:
    """Configure structured JSON logging for the entire application."""
    
    handler = logging.StreamHandler(sys.stdout)
    
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "service",
        },
        static_fields={"app": service_name},
    )
    
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Suppress noisy third-party loggers
    for noisy in ["uvicorn.access", "httpx", "httpcore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
