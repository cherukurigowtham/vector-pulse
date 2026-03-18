from fastapi import APIRouter, Depends, Request
from app.services.merchant.analytics_service import AnalyticsService
from app.repositories.factory import get_risk_repo
from app.core.security import require_role

router = APIRouter(prefix="/merchant/reporting", tags=["Merchant Analytics"])

def get_analytics_service() -> AnalyticsService:
    return AnalyticsService(get_risk_repo())

@router.get("/summary", summary="Get executive dashboard summary.")
async def get_summary(
    session: dict = Depends(require_role(["ADMIN", "ANALYST"])),
    service: AnalyticsService = Depends(get_analytics_service)
):
    return await service.get_executive_summary(session["team_id"])
