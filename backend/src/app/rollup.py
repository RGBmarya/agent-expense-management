"""Materialized rollup computation for cost_rollups table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CostRollup, Event, RollupPeriod
from app.queries import cost_col


async def aggregate_rollups(
    session: AsyncSession,
    org_id: str,
    period: RollupPeriod,
    period_start: datetime,
    period_end: datetime,
) -> int:
    """Aggregate events for the given org/period window into cost_rollups.

    Uses an upsert strategy: delete existing rollups for the window then
    insert fresh aggregates so the data is always consistent.

    Returns the number of rollup rows written.
    """
    # 1. Delete stale rollups for this window
    await session.execute(
        delete(CostRollup).where(
            CostRollup.org_id == org_id,
            CostRollup.period == period,
            CostRollup.period_start == period_start,
        )
    )

    # 2. Aggregate events
    stmt = (
        select(
            func.coalesce(Event.event_type, "").label("event_type"),
            func.coalesce(Event.provider, "").label("provider"),
            func.coalesce(Event.model, "").label("model"),
            func.coalesce(Event.team, "").label("team"),
            func.coalesce(Event.project, "").label("project"),
            func.coalesce(Event.environment, "").label("environment"),
            func.sum(cost_col()).label("total_cost_usd"),
            func.count().label("request_count"),
        )
        .where(
            Event.org_id == org_id,
            Event.timestamp >= period_start,
            Event.timestamp < period_end,
        )
        .group_by(
            Event.event_type,
            Event.provider,
            Event.model,
            Event.team,
            Event.project,
            Event.environment,
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    # 3. Insert new rollups
    for row in rows:
        rollup = CostRollup(
            org_id=org_id,
            period=period,
            period_start=period_start,
            event_type=str(row.event_type),
            provider=str(row.provider),
            model=str(row.model),
            team=str(row.team),
            project=str(row.project),
            environment=str(row.environment),
            total_cost_usd=row.total_cost_usd or Decimal(0),
            request_count=row.request_count or 0,
        )
        session.add(rollup)

    await session.flush()
    return len(rows)


async def run_hourly_rollup(session: AsyncSession, org_id: str) -> int:
    """Convenience wrapper: compute the hourly rollup for the most recent full hour."""
    from datetime import timedelta, timezone

    now = datetime.now(timezone.utc)
    # Roll back to the start of the previous full hour
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    prev_hour = current_hour - timedelta(hours=1)

    return await aggregate_rollups(
        session,
        org_id=org_id,
        period=RollupPeriod.hourly,
        period_start=prev_hour,
        period_end=current_hour,
    )
