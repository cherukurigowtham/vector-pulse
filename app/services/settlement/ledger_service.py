import time
import logging
import secrets
import json
from decimal import Decimal
from app.core.redis import r
from app.core.infrastructure.base_service import BaseService
from app.services.monitoring.alerter import alerter

class LedgerService(BaseService):
    """
    Phase 13: Universal Ledger.
    Manages instant T-0 settlement for high-trust transactions.
    """
    def __init__(self):
        super().__init__("UniversalLedger")

    async def instant_settle(self, merchant_id: str, amount: float, risk_id: str):
        """
        Executes an autonomous settlement.
        Bypasses the 3-7 day banking float.
        """
        try:
            settlement_id = f"ULP_{secrets.token_hex(6).upper()}"
            timestamp = time.time()
            
            # 1. Update Merchant Sovereign Balance
            balance_key = f"ledger:balance:{merchant_id}"
            await r.hincrbyfloat(balance_key, "avail_now", amount)
            await r.hincrbyfloat(balance_key, "total_cleared", amount)
            
            # 2. Record Ledger Entry (Append-only immutable log)
            entry = {
                "id": settlement_id,
                "risk_id": risk_id,
                "merchant": merchant_id,
                "amt": amount,
                "currency": "INR",
                "status": "INSTANT_CLEARED",
                "ts": timestamp,
                "protocol": "ULP v1.0 (Quantum-Ready)"
            }
            
            # Push to a Global Settlement Stream for auditing/NOC
            await r.xadd("ledger:global:stream", {"data": json.dumps(entry)})
            
            # 3. Aggressive Cache for Dashboard live-metrics
            await r.incrbyfloat("ledger:global:total_settled_val", amount)
            await r.incr("ledger:global:tx_count")
            
            # 4. Sovereign Alerting (Solo-Dev Ops)
            if amount >= 100000:
                await alerter.send_milestone("MAJOR_PLANETARY_SETTLEMENT", amount)

            logging.info(f"[$10T] Instant Settlement Executed: {settlement_id} for {merchant_id} | Amount: {amount}")
            return entry
            
        except Exception as e:
            logging.error(f"Ledger Settlement Failed: {e}")
            return None

    async def get_balance(self, merchant_id: str):
        """Returns the sovereign balance and settlement stats."""
        data = await r.hgetall(f"ledger:balance:{merchant_id}")
        return {
            "available": float(data.get("avail_now") or 0.0),
            "total_cleared": float(data.get("total_cleared") or 0.0),
            "currency": "INR",
            "settlement_rail": "ULP (Universal Ledger Protocol)"
        }

ledger_service = LedgerService()
