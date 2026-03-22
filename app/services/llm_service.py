import logging
import json
import aiohttp
from typing import Dict, Any
from app.core.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

class LLMService:
    """
    Interface for Gemini AI to provide Cognitive Forensics.
    """
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    async def generate_adjudication(self, audit_record: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Calls Gemini to synthesize a human-readable fraud adjudication.
        """
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set. Falling back to deterministic narrative.")
            return ""

        prompt = self._build_forensic_prompt(audit_record, context)
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.2,
                        "topP": 0.8,
                        "topK": 40,
                        "maxOutputTokens": 400,
                    }
                }
                async with session.post(f"{self.endpoint}?key={self.api_key}", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['candidates'][0]['content']['parts'][0]['text'].strip()
                    else:
                        error_text = await resp.text()
                        logger.error(f"Gemini API Error ({resp.status}): {error_text}")
                        return ""
        except Exception as e:
            logger.error(f"LLM Synthesis Failed: {e}")
            return ""

    def _build_forensic_prompt(self, audit: Dict, context: Dict) -> str:
        reasons = audit.get("reasons", "").split(",")
        score = audit.get("risk_score", 0)
        decision = audit.get("decision", "UNKNOWN")
        
        prompt = f"""
        You are a Senior Fraud Forensic Analyst at Vantix, an Indian e-commerce RTO protection firm.
        Analyze the following high-risk event and provide a concise, high-impact "Adjudication Narrative" for the merchant.
        
        ### EVENT DETAILS
        - Risk ID: {audit.get('risk_id')}
        - Decision: {decision}
        - Composite Risk Score: {score}/100
        - Active Fraud Signals: {', '.join(reasons)}
        
        ### CONTEXTUAL METRICS
        {json.dumps(context.get('metrics', {}), indent=2)}
        
        ### INSTRUCTIONS
        1. Explain WHY the decision was made using the signals provided.
        2. Specifically mention physical-mathematical anomalies if "IMPOSSIBLE_TRAVEL" is present.
        3. Mention bot-like behavior if "BOT_SPEED" or "COGNITIVE_ANOMALY" is present.
        4. Use a professional, authoritative, yet helpful tone.
        5. Keep the narrative under 100 words.
        
        Narrative:
        """
        return prompt

llm_service = LLMService()
