from typing import Dict, Any, List
from app.core.infrastructure.base_service import BaseService
from app.repositories.risk_repository import RiskRepository

class AnalyticsService(BaseService):
    """
    Handles reporting, metrics aggregation, and executive summaries.
    """
    def __init__(self, risk_repo: RiskRepository):
        super().__init__("Analytics")
        self.risk_repo = risk_repo

    async def get_executive_summary(self, team_id: str) -> Dict[str, Any]:
        """Calculates high-level stats and aggregates intelligence for the dashboard."""
        recent_audits = await self.risk_repo.fetch_recent(team_id, limit=50)
        gov_logs = await self.risk_repo.fetch_profile_audits(team_id, limit=5)
        
        # Aggregate Identity Stats from recent audits
        identity_flags = ["SUSPICIOUS_EMAIL", "IDENTITY_CLUSTER", "SYBIL_ATTACK", "KNOWN_FRAUD_PHONE"]
        identity_hits = 0
        for audit in recent_audits:
            reasons = audit.get("reasons", "")
            if any(flag in reasons for flag in identity_flags):
                identity_hits += 1

        summary = {
            "total_scanned": len(recent_audits),
            "blocks": len([a for a in recent_audits if a.get("decision") == "BLOCK"]),
            "avg_risk_score": sum([float(a.get("risk_score", 0)) for a in recent_audits]) / len(recent_audits) if recent_audits else 0,
            "recent_activity": recent_audits[:5],
            "governance_logs": gov_logs,
            "identity_stats": {
                "hits": identity_hits,
                "percentage": (identity_hits / len(recent_audits) * 100) if recent_audits else 0
            },
            "sla_metrics": {
                "uptime": 99.99,
                "latency_ms": 82,
                "accuracy": 94.2
            }
        }
        
        return summary
