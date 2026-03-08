"""FastAPI application entry point for AgentLedger."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import alerts, auth, dashboard, events, reports


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

# -- CORS ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Routers -------------------------------------------------------------------
app.include_router(events.router, prefix="/v1", tags=["Events"])
app.include_router(dashboard.router, prefix="/v1", tags=["Dashboard"])
app.include_router(alerts.router, prefix="/v1", tags=["Alerts"])
app.include_router(auth.router, prefix="/v1", tags=["Auth"])
app.include_router(reports.router, prefix="/v1", tags=["Reports"])


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
