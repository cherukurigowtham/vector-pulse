import logging
import time
import json
from typing import Dict, Any, List, Optional
from app.core.redis import rk

logger = logging.getLogger(__name__)

class ActionEngine:
    """
    Evaluates merchant-defined automation rules against risk results.
    Rules are stored in Redis under 'rules:{merchant_email}'
    Actions taken are logged in 'actions:{merchant_email}'
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_rules(self, merchant_id: str) -> List[Dict[str, Any]]:
        rules_json = await self.redis.get(rk(f"rules:{merchant_id}"))
        if not rules_json:
            # Default empty ruleset
            return []
        return json.loads(rules_json)

    async def save_rules(self, merchant_id: str, rules: List[Dict[str, Any]]):
        await self.redis.set(rk(f"rules:{merchant_id}"), json.dumps(rules))

    async def evaluate(self, merchant_id: str, risk_result: Dict[str, Any], event_data: Dict[str, Any]):
        """
        evaluates risk_result against merchant rules and triggers actions.
        """
        rules = await self.get_rules(merchant_id)
        score = risk_result.get("risk_score", 0)
        
        actions_triggered = []
        
        for rule in rules:
            threshold = rule.get("threshold", 100)
            action_type = rule.get("action", "NOTIFY") # CANCEL, VERIFY, NOTIFY
            
            if score >= threshold:
                action_info = {
                    "rule_id": rule.get("id"),
                    "action": action_type,
                    "order_id": event_data.get("uid"),
                    "score": score,
                    "timestamp": time.time(),
                    "status": "EXECUTED"
                }
                
                # Logic for specific actions
                if action_type == "CANCEL":
                    # In a real app, this would call merchant's Order API
                    logger.info(f"AUTO-CANCEL triggered for {event_data.get('uid')} (score: {score})")
                elif action_type == "VERIFY":
                    logger.info(f"AUTO-VERIFY (OTP) triggered for {event_data.get('uid')}")
                    # Simulate sending OTP
                    action_info["verification_token"] = "sim_token_" + str(int(time.time()))
                
                actions_triggered.append(action_info)
                await self._log_action(merchant_id, action_info)

        return actions_triggered

    async def _log_action(self, merchant_id: str, action_info: Dict[str, Any]):
        key = rk(f"actions:{merchant_id}")
        await self.redis.lpush(key, json.dumps(action_info))
        await self.redis.ltrim(key, 0, 99) # Keep last 100 actions

    async def get_action_history(self, merchant_id: str) -> List[Dict[str, Any]]:
        key = rk(f"actions:{merchant_id}")
        items = await self.redis.lrange(key, 0, -1)
        return [json.loads(i) for i in items]
