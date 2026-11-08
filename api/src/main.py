from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.src.config import settings
from api.src.services.payment.factory import get_payment_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    yield
    # Shutdown actions


app = FastAPI(
    title="Vouch API",
    description="Hold, Verify, Release donation escrow system running on PayPal rails with AI auditing.",
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
        "database": "configured",
    }
