from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from app.models import Order

@dataclass(slots=True)
class RiskContext:
    """
    Google-Style DTO for sharing state across risk pillars.
    Optimized with __slots__ to minimize memory overhead.
    """
    order: Order
    merchant_email: str
    merchant_key_hash: Optional[str] = None
    
    # Shared results to avoid redundant computations
    geoip_result: Dict[str, Any] = field(default_factory=dict)
    vector_hash: Optional[str] = None
    consortium_hits: int = 0
    reputation_map: Dict[str, float] = field(default_factory=dict)
    
    # Risk calculation state
    flags: List[str] = field(default_factory=list)
    impacts: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Internal state
    is_quarantined: bool = False
    trust_score: float = 50.0
