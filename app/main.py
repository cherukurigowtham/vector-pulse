from fastapi import FastAPI
from app.api.v1.risk import analysis as risk_analysis
from app.api.v1.merchant import profile, team, reporting, payments
from app.api.v1.security import auth, vault
from app.core.config import ENVIRONMENT, CORS_ALLOW_ORIGINS
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import AUDIT_STORE

@asynccontextmanager
async def lifespan(app: FastAPI):
    await AUDIT_STORE.init()
    yield
    await AUDIT_STORE.close()

app = FastAPI(
    title="Vantix RTO Shield - Google-Style Refactor",
    version="2.0.0",
    lifespan=lifespan
)

# Professional CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import public

# ... (other imports)

app.include_router(public.router)
app.include_router(risk_analysis.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(vault.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(team.router, prefix="/api/v1")
app.include_router(reporting.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0-modular"}
