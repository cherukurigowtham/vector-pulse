from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
import unicodedata
from typing import Any, Literal, List, Dict
from app.services.tokenization_service import token_service

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
    card_bin: str | None = Field(None, pattern=r"^\d{6}$")
    checkout_time_secs: float | None = Field(None, ge=0)
    # Behavioral DNA Fields
    keystroke_velocity: float | None = Field(None, ge=0)
    mouse_movement_entropy: float | None = Field(None, ge=0)
    session_id: str | None = Field(None, min_length=16, max_length=128)
    shadow: bool = False

    @field_validator("uid", "addr", "name", "email", "phone", "ip", "device_hash", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            # Strip control characters (C0 & C1)
            v = "".join(ch for ch in v if unicodedata.category(ch)[0] != "C")
            return v.strip()
        return v

    def tokenize(self) -> "Order":
        """
        Zero-Trust Enforcer: Explicitly converts toxic PII into Identity Shadows.
        Should be called after all intelligence lookups (GeoIP, etc.) are complete.
        """
        if not getattr(self, "_tokenized", False):
            # Create safe display version of email for logs
            if self.email:
                self.name = f"{token_service.anonymize_email(self.email)} (Shadow)"
            
            # Tokenize hot fields
            self.email = token_service.tokenize(self.email)
            self.phone = token_service.tokenize(self.phone)
            self.ip = token_service.tokenize_ip(self.ip)
            self.addr = token_service.tokenize(self.addr) # High-entropy address shadow
            
            # Mark as tokenized to avoid double-hashing
            object.__setattr__(self, "_tokenized", True)
            
        return self

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
    full_name: str | None = Field(None, min_length=2, max_length=100)
    company_name: str | None = Field(None, min_length=2, max_length=128)
    merchant_category: str | None = Field(None, max_length=64)
    expected_monthly_volume: str | None = Field(None, max_length=32)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

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

class WebhookSettingsUpdate(BaseModel):
    alert_webhook_url: str | None = Field(None, max_length=512)
    webhook_secret: str | None = Field(None, min_length=16, max_length=64)

class AutomationRule(BaseModel):
    id: str
    threshold: float = Field(..., ge=0, le=100)
    action: Literal["CANCEL", "VERIFY", "NOTIFY"]

class AutomationRulesUpdate(BaseModel):
    rules: List[AutomationRule]

class ClickstreamEvent(BaseModel):
    event_type: str = Field(..., description="E.g., click, scroll, hover, focus, blur")
    element: str | None = None
    x: int | None = None
    y: int | None = None
    dwell_time_ms: int | None = Field(None, ge=0)
    path: str = Field(..., description="The URL path where the event occurred")
    timestamp: float = Field(..., description="Client-side timestamp")

class BehavioralIngestRequest(BaseModel):
    session_id: str = Field(..., min_length=16, max_length=128)
    events: List[ClickstreamEvent]
    client_metadata: Dict[str, Any] = Field(default_factory=dict)

class ForensicReport(BaseModel):
    risk_id: str
    decision: str
    score: float
    report_markdown: str
    generated_at: float
