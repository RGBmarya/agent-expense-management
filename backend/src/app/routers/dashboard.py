"""Dashboard read endpoints – overview, explore, spend-over-time."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_org
from app.database import get_session
from app.models import Event, Organization
from app.queries import build_event_filters, cost_col
from app.schemas import (
    BreakdownItem,
    ExploreResponse,
    ExploreRow,
    OverviewResponse,
    SpendOverTimeResponse,
    SpendTimeseriesPoint,
    TrendPoint,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /v1/dashboard/overview
# ---------------------------------------------------------------------------

@router.get("/dashboard/overview", response_model=OverviewResponse)
async def dashboard_overview(
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> OverviewResponse:
    """Month-to-date spend, previous MTD for comparison, 30-day trend, top breakdowns."""
    now = datetime.now(timezone.utc)
    mtd_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Previous month MTD (same day-of-month range)
    if now.month == 1:
        prev_mtd_start = mtd_start.replace(year=now.year - 1, month=12)
    else:
        prev_mtd_start = mtd_start.replace(month=now.month - 1)
    prev_mtd_end = prev_mtd_start + (now - mtd_start)

    # Top breakdowns helper
    async def _top(col, limit: int = 5) -> list[BreakdownItem]:
        stmt = (
            select(
                col.label("key"),
                func.coalesce(func.sum(cost_col()), Decimal(0)).label("total_cost_usd"),
                func.count().label("request_count"),
            )
            .where(Event.org_id == org.id, Event.timestamp >= mtd_start)
            .group_by(col)
            .order_by(func.sum(cost_col()).desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
        return [
            BreakdownItem(
                key=str(r.key or "unknown"),
                total_cost_usd=r.total_cost_usd,
                request_count=r.request_count,
            )
            for r in rows
        ]

    # Run independent queries concurrently
    async def _mtd_spend() -> Decimal:
        result = await session.execute(
            select(func.coalesce(func.sum(cost_col()), Decimal(0))).where(
                Event.org_id == org.id,
                Event.timestamp >= mtd_start,
            )
        )
        return result.scalar_one()

    async def _prev_mtd_spend() -> Decimal:
        result = await session.execute(
            select(func.coalesce(func.sum(cost_col()), Decimal(0))).where(
                Event.org_id == org.id,
                Event.timestamp >= prev_mtd_start,
                Event.timestamp < prev_mtd_end,
            )
        )
        return result.scalar_one()

    async def _trend_30d() -> list[TrendPoint]:
        thirty_days_ago = now - timedelta(days=30)
        trend_stmt = (
            select(
                func.date_trunc("day", Event.timestamp).label("day"),
                func.coalesce(func.sum(cost_col()), Decimal(0)).label("total_cost_usd"),
                func.count().label("request_count"),
            )
            .where(Event.org_id == org.id, Event.timestamp >= thirty_days_ago)
            .group_by("day")
            .order_by("day")
        )
        rows = (await session.execute(trend_stmt)).all()
        return [
            TrendPoint(
                date=row.day.isoformat() if row.day else "",
                total_cost_usd=float(row.total_cost_usd),
                request_count=row.request_count,
            )
            for row in rows
        ]

    (
        mtd_spend,
        prev_mtd_spend,
        trend_30d,
        top_providers,
        top_models,
        top_teams,
    ) = await asyncio.gather(
        _mtd_spend(),
        _prev_mtd_spend(),
        _trend_30d(),
        _top(Event.provider),
        _top(Event.model),
        _top(Event.team),
    )

    return OverviewResponse(
        mtd_spend_usd=mtd_spend,
        previous_mtd_spend_usd=prev_mtd_spend,
        trend_30d=trend_30d,
        top_providers=top_providers,
        top_models=top_models,
        top_teams=top_teams,
    )


# ---------------------------------------------------------------------------
# GET /v1/dashboard/explore
# ---------------------------------------------------------------------------

@router.get("/dashboard/explore", response_model=ExploreResponse)
async def dashboard_explore(
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> ExploreResponse:
    """Filterable drill-down grouped by provider/model/team/project/environment."""
    filters = build_event_filters(
        org.id,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        model=model,
        team=team,
        project=project,
        environment=environment,
    )

    group_cols = [Event.provider, Event.model, Event.team, Event.project, Event.environment]

    count_stmt = (
        select(func.count())
        .select_from(
            select(*group_cols)
            .where(*filters)
            .group_by(*group_cols)
            .subquery()
        )
    )
    total = (await session.execute(count_stmt)).scalar_one()

    data_stmt = (
        select(
            Event.provider,
            Event.model,
            Event.team,
            Event.project,
            Event.environment,
            func.coalesce(func.sum(cost_col()), Decimal(0)).label("total_cost_usd"),
            func.count().label("request_count"),
        )
        .where(*filters)
        .group_by(*group_cols)
        .order_by(func.sum(cost_col()).desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(data_stmt)).all()

    return ExploreResponse(
        rows=[
            ExploreRow(
                provider=r.provider,
                model=r.model,
                team=r.team,
                project=r.project,
                environment=r.environment,
                total_cost_usd=r.total_cost_usd,
                request_count=r.request_count,
            )
            for r in rows
        ],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /v1/dashboard/spend-over-time
# ---------------------------------------------------------------------------

@router.get("/dashboard/spend-over-time", response_model=SpendOverTimeResponse)
async def spend_over_time(
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    granularity: Literal["hourly", "daily", "monthly"] = Query("daily"),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
) -> SpendOverTimeResponse:
    """Time-series spend data for charting."""
    now = datetime.now(timezone.utc)
    if start_date is None:
        start_date = now - timedelta(days=30)
    if end_date is None:
        end_date = now

    filters = build_event_filters(
        org.id,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        model=model,
        team=team,
    )

    trunc = func.date_trunc(granularity if granularity != "daily" else "day", Event.timestamp)

    stmt = (
        select(
            trunc.label("period_start"),
            func.coalesce(func.sum(cost_col()), Decimal(0)).label("total_cost_usd"),
            func.count().label("request_count"),
        )
        .where(*filters)
        .group_by("period_start")
        .order_by("period_start")
    )
    rows = (await session.execute(stmt)).all()

    return SpendOverTimeResponse(
        data=[
            SpendTimeseriesPoint(
                period_start=r.period_start,
                total_cost_usd=r.total_cost_usd,
                request_count=r.request_count,
            )
            for r in rows
        ],
        granularity=granularity,
    )
