import time
from app.models.schemas import ForensicReport
from app.models.dto.risk_context import RiskContext

class ForensicsService:
    """
    Explainable AI (XAI) Forensics (Phase 14).
    Synthesizes complex pillar impacts into human-readable reasoning.
    """

    def generate_report(self, risk_id: str, context: RiskContext, decision: str, score: float) -> ForensicReport:
        """
        Synthesizes a professional forensic report based on multi-pillar results.
        """
        narrative = [f"### Forensic Report: {risk_id}", f"**Decision**: {decision} (Score: {score:.1f}/100)", ""]
        
        impacts = context.impacts
        flags = context.flags
        
        # 1. Primary Vector Identification
        narrative.append("#### Analysis Summary")
        if score > 50:
            primary_finding = "High-Risk Vector Spotted"
            narrative.append("The transaction was flagged as high-risk primarily due to a convergence of multiple suspicious indicators.")
        else:
            primary_finding = "Standard Risk Profile"
            narrative.append("The transaction was allowed as the risk indicators fell within the merchant's safety parameters.")
            
        # 2. Detailed Findings
        narrative.append("\n#### Detailed Findings")
        for flag in flags:
            if "HIGH_VELOCITY" in flag:
                narrative.append("- **Velocity Anomaly**: A rapid burst of orders was detected, exceeding the standard baseline for this user profile.")
            elif "IDENTITY_CLUSTER" in flag:
                narrative.append("- **Identity Clustering**: The transaction shares attributes (IP Subnet or Pin) with a known high-risk cluster.")
            elif "SHIELD_MODE_ACTIVE" in flag:
                narrative.append("- **Adaptive Shielding**: System-wide block thresholds were tightened due to high-attack volume, making the engine more sensitive to the markers found in this request.")
            elif "FRAUD_RING" in flag:
                narrative.append("- **Cross-Merchant Linkage**: Our Global Pulse network identified this identity across multiple other merchant platforms within a short window.")
            elif "BEHAVIORAL_ANOMALY" in flag:
                 narrative.append("- **Robotic Automation**: Interaction sequences (click-to-focus deltas) indicate a high probability of automated bot script execution.")
        
        # 3. Mitigation Strategy
        narrative.append("\n#### Recommended Mitigation")
        if decision == "BLOCK":
            narrative.append("1. **Verify Identity**: Require manual document upload or multi-factor authentication (MFA).")
            narrative.append("2. **Address Review**: Manually inspect the shipping address for PO boxes or high-risk forwarding hubs.")
        else:
            narrative.append("No immediate action required, but monitor for future velocity spikes.")
            
        return ForensicReport(
            risk_id=risk_id,
            decision=decision,
            score=score,
            report_markdown="\n".join(narrative),
            generated_at=time.time()
        )

forensics_service = ForensicsService()
