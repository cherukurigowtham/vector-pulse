from app.repositories.merchant_repository import MerchantRepository
from app.repositories.risk_repository import RiskRepository

# Factory for Repositories
_merchant_repo = MerchantRepository()
_risk_repo = RiskRepository()

def get_merchant_repo() -> MerchantRepository:
    return _merchant_repo

def get_risk_repo() -> RiskRepository:
    return _risk_repo
