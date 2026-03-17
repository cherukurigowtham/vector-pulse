from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import require_api_key
from app.services.forensics_service import forensics_service

router = APIRouter(tags=["forensics"])

@router.post("/v1/forensics/ask", summary="Query the Vantix AI Forensic Assistant")
async def ask_forensics(
    risk_id: str = Body(..., embed=True),
    query: str = Body(None, embed=True),
    key_data: dict = Depends(require_api_key)
):
    """
    Forensic AI Assistant.
    Provides natural language explanations for complex risk decisions.
    """
    merchant_email = key_data.get("email")
    
    analysis = await forensics_service.analyze_decision(risk_id, merchant_email)
    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])
        
    return analysis
