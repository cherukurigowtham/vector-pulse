from prometheus_client import Counter, Gauge, CollectorRegistry, generate_latest

# Global registry for custom application metrics
REG = CollectorRegistry()
risk_events_total = Counter(
    "vp_risk_events_total", "Total risk analysis events processed", registry=REG
)
risk_score_gauge = Gauge(
    "vp_risk_score", "Latest risk score for a processed event", registry=REG
)


def get_metrics() -> bytes:
    # Return Prometheus metrics in text format; aggregation via the global REG
    return generate_latest(REG)
