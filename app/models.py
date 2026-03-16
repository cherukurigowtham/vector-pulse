from pydantic import BaseModel, Field, EmailStr, field_validator
import unicodedata
from typing import Any, Literal

class Order(BaseModel):
    uid: str = Field(..., min_length=1, max_length=64)
    amt: float = Field(..., gt=0)
    addr: str = Field(..., min_length=5, max_length=512)
    pin: str = Field(..., pattern=r"^\d{6}$")
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, max_length=128)
    phone: str | None = Field(None, pattern=r"^[6-9]\d{9}$")
    ip: str = Field("127.0.0.1", pattern=r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$|([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}$")
    device_hash: str | None = Field(None, min_length=16, max_length=128)
    checkout_time_secs: float | None = Field(None, ge=0)
    # Behavioral DNA Fields
    keystroke_velocity: float | None = Field(None, ge=0)
    mouse_movement_entropy: float | None = Field(None, ge=0)
    shadow: bool = False

    @field_validator("uid", "addr", "name", "email", "phone", "ip", "device_hash", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            # Strip control characters (C0 & C1)
            v = "".join(ch for ch in v if unicodedata.category(ch)[0] != "C")
            return v.strip()
        return v

class RegisterRequest(BaseModel):
    email: str
    plan: str = "starter"
    admin_key: str

class AdminSessionRequest(BaseModel):
    admin_key: str

class RiskConfigUpdateRequest(BaseModel):
    history_len: int | None = None
    z_score_threshold: float | None = None
    velocity_window_secs: int | None = None
    velocity_max_orders: int | None = None
    sybil_address_limit: int | None = None
    decision_threshold: float | None = None
    velocity_weight: float | None = None
    sybil_weight: float | None = None
    anomaly_weight: float | None = None
    identity_weight: float | None = None
    cohort_weight: float | None = None
    vpn_weight: float | None = None
    trust_floor: float | None = None
    trust_penalty_multiplier: float | None = None
    burst_fraction_per_minute: float | None = None
    savings_per_block_inr: int | None = None
    review_threshold: float | None = None
    global_network_weight: float | None = None
    gibberish_weight: float | None = None
    device_velocity_weight: float | None = None
    suspicious_name_weight: float | None = None
    geo_velocity_weight: float | None = None
    time_anomaly_weight: float | None = None
    bot_speed_weight: float | None = None
    suspicious_phone_weight: float | None = None
    disposable_email_weight: float | None = None

class PublicRegisterRequest(BaseModel):
    email: str

class PilotRequest(BaseModel):
    name: str
    email: str
    company: str
    category: str
    monthly_orders: str
    cod_share: str

class PilotRequestStatusUpdate(BaseModel):
    status: Literal["new", "contacted", "pilot_started", "won", "closed"]

class PilotRequestDetailUpdate(BaseModel):
    assigned_to: str | None = None
    notes: str | None = None

class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class MerchantSettingsUpdate(BaseModel):
    company_name: str | None = None
    category: str | None = None
    monthly_orders: str | None = None
    cod_share: str | None = None

class UpgradeRequest(BaseModel):
    requested_plan: Literal["growth", "managed"]
    note: str | None = None

class UpgradeRequestDecision(BaseModel):
    status: Literal["approved", "rejected"]

class OutcomeUpdate(BaseModel):
    risk_id: str
    status: Literal["DELIVERED", "RTO", "FRAUD_CONFIRMED"]
    reason: str | None = Field(None, max_length=200)
