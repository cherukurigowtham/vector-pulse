import logging
import json
from typing import Dict, Any
from app.db.database import AUDIT_STORE
from app.core.redis import r

logger = logging.getLogger(__name__)

class ForensicsService:
    """
    LLM-Forensics Assistant (Phase 14).
    Synthesizes complex signals into human-readable adjudication narratives.
    """
    
    async def analyze_decision(self, risk_id: str, merchant_email: str) -> Dict[str, Any]:
        # 1. Fetch historical record from DB
        audit = await AUDIT_STORE.fetch_risk_audit(risk_id)
        if not audit:
            return {"error": "Audit Record Not Found"}
            
        # 2. Fetch runtime context from Redis
        explain_data = await r.get(f"explain:{risk_id}")
        context = json.loads(explain_data) if explain_data else {}
        
        # 3. LLM-Style Synthesis (Deterministic Forensic Logic)
        narrative = self._synthesize_forensic_narrative(audit, context)
        
        return {
            "risk_id": risk_id,
            "adjudication_narrative": narrative,
            "forensic_signals": {
                "behavioral": context.get("metrics", {}).get("behavioral_dna", "N/A"),
                "network": "LINKED_DEVICE_CLUSTER" if "IDENTITY_CLUSTER_DETECTED" in audit["reasons"] else "ISOLATED_DEVICE",
                "geographic": "ACCELERATED_VELOCITY" if "IMPOSSIBLE_TRAVEL" in audit["reasons"] else "STABLE_LOCATION"
            },
            "recommendation": "EXAMINE_FOR_CHARGEBACK" if audit["risk_score"] > 80 else "LOW_CONCERN"
        }

    def _synthesize_forensic_narrative(self, audit: Dict, context: Dict) -> str:
        score = audit["risk_score"]
        reasons = audit["reasons"].split(",") if audit["reasons"] else []
        
        intro = f"Investigation into Decision {audit['risk_id']} confirms a high-accuracy detection. "
        
        analysis = ""
        if "GLOBAL_CONSORTIUM_BLOCK" in reasons:
            analysis += "This identity is blacklisted network-wide across the Vantix pulse network. "
        if "COGNITIVE_ANOMALY_DETECTED" in reasons:
            analysis += "Behavioral transformers identified non-human interaction entropy, suggesting an automated script using human proxies. "
        if "IMPOSSIBLE_TRAVEL" in reasons:
            analysis += "The distance-time velocity exceeded physical human limits (Impossible Travel). "
            
        conclusion = f"Conclusion: The {audit['decision']} action was justified by a composite risk score of {score:.1f} across {len(reasons)} independent fraud vectors."
        
        return intro + analysis + conclusion

forensics_service = ForensicsService()
