import os
from typing import Any

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None else default

def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None else default

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
AUDIT_DB = "audit_log.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
PILOT_REQUEST_WEBHOOK_URL = os.getenv("PILOT_REQUEST_WEBHOOK_URL", "").strip()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"

CORS_ALLOW_ORIGINS = [
    origin.strip() 
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") 
    if origin.strip()
] or [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

RATE_LIMITS = {
    "free": 1_000,
    "starter": 10_000,
    "growth": 100_000,
    "scale": 1_000_000,
}

RISK_CONFIG = {
    "history_len": _env_int("RISK_HISTORY_LEN", 10),
    "z_score_threshold": _env_float("RISK_Z_SCORE_THRESHOLD", 3.0),
    "velocity_window_secs": _env_int("RISK_VELOCITY_WINDOW_SECS", 5),
    "velocity_max_orders": _env_int("RISK_VELOCITY_MAX_ORDERS", 3),
    "sybil_address_limit": _env_int("RISK_SYBIL_ADDRESS_LIMIT", 3),
    "decision_threshold": _env_float("RISK_DECISION_THRESHOLD", 40.0),
    "velocity_weight": _env_float("RISK_WEIGHT_VELOCITY", 35.0),
    "sybil_weight": _env_float("RISK_WEIGHT_SYBIL", 25.0),
    "anomaly_weight": _env_float("RISK_WEIGHT_ANOMALY", 20.0),
    "identity_weight": _env_float("RISK_WEIGHT_IDENTITY", 18.0),
    "cohort_weight": _env_float("RISK_WEIGHT_COHORT", 12.0),
    "vpn_weight": _env_float("RISK_WEIGHT_VPN", 15.0),
    "trust_floor": _env_float("RISK_TRUST_FLOOR", 30.0),
    "trust_penalty_multiplier": _env_float("RISK_TRUST_PENALTY_MULTIPLIER", 0.5),
    "burst_fraction_per_minute": _env_float("RATE_LIMIT_BURST_FRACTION", 0.001),
    "savings_per_block_inr": _env_int("RISK_SAVINGS_PER_BLOCK_INR", 70),
    "review_threshold": _env_float("RISK_REVIEW_THRESHOLD", 28.0),
    "global_network_weight": _env_float("RISK_WEIGHT_GLOBAL", 45.0),
    "gibberish_weight": _env_float("RISK_WEIGHT_GIBBERISH", 30.0),
    "device_velocity_weight": _env_float("RISK_WEIGHT_DEVICE_VELOCITY", 40.0),
    "suspicious_name_weight": _env_float("RISK_WEIGHT_SUSPICIOUS_NAME", 20.0),
    "geo_velocity_weight": _env_float("RISK_WEIGHT_GEO_VELOCITY", 40.0),
    "time_anomaly_weight": _env_float("RISK_WEIGHT_TIME_ANOMALY", 10.0),
    "bot_speed_weight": _env_float("RISK_WEIGHT_BOT_SPEED", 50.0),
    "suspicious_phone_weight": _env_float("RISK_WEIGHT_SUSPICIOUS_PHONE", 30.0),
    "disposable_email_weight": _env_float("RISK_WEIGHT_DISPOSABLE_EMAIL", 45.0),
    "email_name_mismatch_weight": _env_float("RISK_WEIGHT_EMAIL_NAME_MISMATCH", 25.0),
    "poor_address_weight": _env_float("RISK_WEIGHT_POOR_ADDRESS", 15.0),
    "high_risk_pin_weight": _env_float("RISK_WEIGHT_HIGH_RISK_PIN", 35.0),
}

RISK_CONFIG_TYPES = {k: type(v) for k, v in RISK_CONFIG.items()}

RISK_CONFIG_BOUNDS = {
    "history_len": (1, 500),
    "z_score_threshold": (0.1, 10.0),
    "velocity_window_secs": (1, 3600),
    "velocity_max_orders": (1, 1000),
    "sybil_address_limit": (1, 1000),
    "decision_threshold": (0.0, 100.0),
    "velocity_weight": (0.0, 100.0),
    "sybil_weight": (0.0, 100.0),
    "anomaly_weight": (0.0, 100.0),
    "identity_weight": (0.0, 100.0),
    "cohort_weight": (0.0, 100.0),
    "vpn_weight": (0.0, 100.0),
    "trust_floor": (0.0, 100.0),
    "trust_penalty_multiplier": (0.0, 10.0),
    "burst_fraction_per_minute": (0.000001, 1.0),
    "savings_per_block_inr": (1, 1000000),
    "review_threshold": (0.0, 100.0),
    "global_network_weight": (0.0, 100.0),
    "gibberish_weight": (0.0, 100.0),
    "device_velocity_weight": (0.0, 100.0),
    "suspicious_name_weight": (0.0, 100.0),
    "geo_velocity_weight": (0.0, 100.0),
    "time_anomaly_weight": (0.0, 100.0),
    "bot_speed_weight": (0.0, 100.0),
    "suspicious_phone_weight": (0.0, 100.0),
    "disposable_email_weight": (0.0, 100.0),
    "email_name_mismatch_weight": (0.0, 100.0),
    "poor_address_weight": (0.0, 100.0),
    "high_risk_pin_weight": (0.0, 100.0),
}

ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "local-dev-admin-key")
SESSION_COOKIE_SECURE = ENVIRONMENT == "production"
RISK_FAIL_CLOSED = _env_bool("RISK_FAIL_CLOSED", False)  # Default to fail-open (safer for business)
GLOBAL_PULSE_SALT = os.getenv("GLOBAL_PULSE_SALT", "vector-pulse-collective-defense-2024")
