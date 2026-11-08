import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.src.config import settings
from api.src.database import engine
from api.src.models import Base
from api.src.services.payment.factory import get_payment_provider
from api.src.routers.payees import router as payees_router
from api.src.routers.campaigns import router as campaigns_router
from api.src.routers.audits import router as audits_router
from api.src.routers.transparency import router as transparency_router
from api.src.routers.sim import router as sim_router
from api.src.routers.webhooks import router as webhooks_router
from api.src.routers.reference_prices import router as reference_prices_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema exists on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title="Vouch API",
    description="Hold, Verify, Release donation escrow system running on PayPal rails with AI evidence auditing.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount upload storage for evidence viewer
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include modular API routers
app.include_router(payees_router)
app.include_router(campaigns_router)
app.include_router(audits_router)
app.include_router(transparency_router)
app.include_router(sim_router)
app.include_router(webhooks_router)
app.include_router(reference_prices_router)



@app.get("/healthz", tags=["System"])
async def healthz():
    """Health check endpoint required by Render and monitoring."""
    payment_provider = get_payment_provider()
    return {
        "status": "ok",
        "service": "vouch-api",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "payment_provider": settings.PAYMENT_PROVIDER.value,
        "llm_provider": settings.LLM_PROVIDER.value,
        "llm_model": settings.LLM_MODEL,
        "database": "connected",
    }
