import asyncio
from fastapi import FastAPI, Request
from app.api.v1.risk import analysis as risk_analysis
from app.api.v1.risk import forensics
from app.api.v1.merchant import profile, team, reporting, billing
from app.api.v1.security import auth, vault
from app.routers import public, merchant, stream
from app.core.config import CORS_ALLOW_ORIGINS
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import AUDIT_STORE
from app.core.security import verify_jwt
from app.services.discovery.consortium import ConsortiumRing
from app.workers.audit_flusher import run_audit_flusher

@asynccontextmanager
async def lifespan(app: FastAPI):
    await AUDIT_STORE.init()
    consortium_thread = ConsortiumRing.attach_listener()
    flusher_task = asyncio.create_task(run_audit_flusher())
    yield
    flusher_task.cancel()
    try:
        await flusher_task
    except asyncio.CancelledError:
        pass
    if consortium_thread:
        consortium_thread.stop()
    await AUDIT_STORE.close()

app = FastAPI(
    title="Vantix RTO Shield - Google-Style Refactor",
    version="2.0.0",
    lifespan=lifespan
)

# Authentication Middleware (Populates request.state.user from JWT)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    token = request.cookies.get("vp_token")
    if token:
        user = verify_jwt(token)
        if user:
            request.state.user = user
    return await call_next(request)

# Professional CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router, prefix="/api/v1")
app.include_router(merchant.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")
app.include_router(risk_analysis.router, prefix="/api/v1")
app.include_router(forensics.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(vault.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(team.router, prefix="/api/v1")
app.include_router(reporting.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0-modular"}
