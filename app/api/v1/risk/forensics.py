import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.db.database import AUDIT_STORE
from app.core.security import require_role
from app.core.config import GEMINI_API_KEY

router = APIRouter(prefix="/risk", tags=["risk", "forensics"])

class ForensicsResponse(BaseModel):
    risk_id: str
    forensics_report: str
    model: str

@router.get("/forensics/{risk_id}", response_model=ForensicsResponse)
async def generate_forensics_report(risk_id: str, session: dict = Depends(require_role(["ADMIN", "ANALYST"]))):
    """
    Simulates a FAANG-tier Threat Intelligence Agent.
    Queries the audit log for the blocked transaction context and uses the Gemini API
    to orchestrate a deep, actionable technical assessment explaining the risk factors.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="AI Forensics module requires an active GEMINI_API_KEY in the environment."
        )

    merchant_email = session.get("email")
    team_id = session.get("team_id") or merchant_email

    # 1. Fetch exact transaction context natively from the DB store
    raw_audits = await AUDIT_STORE.fetch_recent_risk_audits(team_id, limit=200)
    target_audit = next((a for a in raw_audits if a.get("risk_id") == risk_id), None)

    if not target_audit:
        raise HTTPException(status_code=404, detail="Risk trace sequence not found or ownership denied.")

    score = target_audit.get("risk_score")
    reasons = target_audit.get("reasons", "Anomalous Network Topology")
    decision = target_audit.get("decision", "QUARANTINE_REQUIRED")

    # 2. Construct the highly specialized Zero-Shot System Prompt
    prompt = f"""You are 'Pulse-Core', a specialized Enterprise Threat Intelligence Agent for Vantix.
A commercial transaction was just intercepted by our Edge Rules. Analyze the payload variables and generate a highly technical, concise forensic report in Markdown.
Break down the primary malicious payload attributes. Output 2-3 paragraphs. Sound brutally structural and authoritative.

--- RAW SIGNAL TELEMETRY ---
Risk Trace Identity: {risk_id}
Cumulative ML Entropy Score: {score} / 100.0 (High Risk Vector)
Physical Engine Action: {decision}
Discovered Attack Identifiers: {reasons}
-----------------------------
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 450}
    }

    try:
        # 3. Synchronously dispatch context to Gemini API without external bindings
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
                json=payload,
                timeout=12.0
            )
        resp.raise_for_status()
        data = resp.json()
        report = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        report = f"> **CRITICAL SYSTEM FAILURE:** Neural resolution failed in remote execution context: `{str(e)}`"

    return ForensicsResponse(
        risk_id=risk_id,
        forensics_report=report,
        model="gemini-2.5-flash-native"
    )
