import logging
import json
import time
from fastapi import APIRouter, HTTPException, Request, Depends
from app.models import BehavioralIngestRequest
from app.core.redis import r
from app.core.security import require_api_key

router = APIRouter(prefix="/v1/behavior", tags=["Behavioral Intelligence"])
logger = logging.getLogger(__name__)

@router.post("/ingest", summary="Ingest clickstream behavioral data")
async def ingest_behavior(payload: BehavioralIngestRequest, merchant: dict = Depends(require_api_key)):
    """
    High-throughput behavioral event ingestion.
    Events are stored in a rolling Redis window for sequence analysis (Phase 13).
    """
    merchant_email = merchant["email"]
    session_id = payload.session_id
    
    # Storage Key: session-based behavioral stream
    # Each merchant gets isolated session streams
    key = f"behavior:stream:{merchant_email}:{session_id}"
    
    try:
        async with r.pipeline() as pipe:
            for event in payload.events:
                # Store serialized event in Redis List
                event_data = event.model_dump()
                event_data["server_received_at"] = time.time()
                pipe.rpush(key, json.dumps(event_data))
            
            # Keep only the last 500 events per session to prevent memory bloat
            pipe.ltrim(key, -500, -1)
            # Expire session data after 24 hours of inactivity
            pipe.expire(key, 86400)
            
            await pipe.execute()
            
        logger.debug(f"Ingested {len(payload.events)} events for session {session_id} (Merchant: {merchant_email})")
        return {"status": "success", "events_recorded": len(payload.events)}
        
    except Exception as e:
        logger.error(f"Behavioral ingestion failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to record behavioral signals")
