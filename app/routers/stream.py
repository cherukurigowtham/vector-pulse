import asyncio
import logging
import random
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import verify_jwt

router = APIRouter(tags=["Telemetry"])
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"NOC Telemetry connected securely for {client_id}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                self.active_connections.pop(client_id, None)

    async def broadcast_to_client(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

@router.websocket("/ws/noc")
async def websocket_noc_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    Establishes a persistent, FAANG-tier full-duplex WebSocket connection.
    Verifies the JWT token from the query parameters, then locks into an infinite asyncio loop
    beaming structured transaction telemetry dynamically to update the frontend NOC graphs in real-time.
    """
    user = verify_jwt(token)
    if not user:
        await websocket.close(code=1008)
        return
    
    email = user.get("email")
    if not email:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, email)
    
    try:
        while True:
            # Emulate real-time global traffic (800ms - 2.5s cadence)
            await asyncio.sleep(random.uniform(0.8, 2.5))
            
            # Formulate simulated live threat vectors
            is_threat = random.random() > 0.88
            raw_score = random.uniform(85.0, 99.0) if is_threat else random.uniform(5.0, 35.0)
            score = float(f"{raw_score:.1f}")
            
            payload = {
                "event": "live_telemetry",
                "timestamp": int(time.time()),
                "metrics": {
                    "score": score,
                    "latency_ms": random.randint(12, 45),
                    "action": "BLOCKED" if is_threat else "ALLOWED",
                    "vector": random.choice(["IP_ANOMALY", "VELOCITY_SPIKE", "SYNTHETIC_IDENTITY"]) if is_threat else "NOMINAL"
                }
            }
            
            await manager.broadcast_to_client(payload, email)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, email)
        logger.info(f"NOC Telemetry disconnected for {email}")
