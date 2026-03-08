"""FastAPI application entry point for AgentLedger."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine
from app.models import Base
from app.rate_limit import limiter
from app.routers import alerts, approvals, auth, cards, dashboard, events, policies, programs, reports, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create tables on startup (dev convenience) and dispose engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="AgentLedger",
    description="AI Expense Management API",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# -- CORS ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# -- Routers -------------------------------------------------------------------
app.include_router(events.router, prefix="/v1", tags=["Events"])
app.include_router(dashboard.router, prefix="/v1", tags=["Dashboard"])
app.include_router(alerts.router, prefix="/v1", tags=["Alerts"])
app.include_router(auth.router, prefix="/v1", tags=["Auth"])
app.include_router(reports.router, prefix="/v1", tags=["Reports"])
app.include_router(cards.router, prefix="/v1", tags=["Cards"])
app.include_router(policies.router, prefix="/v1", tags=["Policies"])
app.include_router(programs.router, prefix="/v1", tags=["Programs"])
app.include_router(approvals.router, prefix="/v1", tags=["Approvals"])
app.include_router(webhooks.router, prefix="/v1", tags=["Webhooks"])


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
