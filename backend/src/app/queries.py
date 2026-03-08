"""Shared query helpers used across routers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func

from app.models import Event


def cost_col() -> func.coalesce:
    """Return a coalesce expression preferring estimated_cost_usd then amount_usd."""
    return func.coalesce(Event.estimated_cost_usd, Event.amount_usd, Decimal(0))


def month_to_range(month: str) -> tuple[datetime, datetime]:
    """Parse a 'YYYY-MM' string into (start, end) datetimes in UTC.

    Returns the first instant of the month and the first instant of the next month.
    """
    from datetime import timezone

    year, mon = map(int, month.split("-"))
    start = datetime(year, mon, 1, tzinfo=timezone.utc)
    if mon == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, mon + 1, 1, tzinfo=timezone.utc)
    return start, end


def build_event_filters(
    org_id: str,
    *,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    team: Optional[str] = None,
    project: Optional[str] = None,
    environment: Optional[str] = None,
) -> list:
    """Build a list of SQLAlchemy WHERE clauses for Event queries."""
    filters = [Event.org_id == org_id]
    if start_date:
        filters.append(Event.timestamp >= start_date)
    if end_date:
        filters.append(Event.timestamp < end_date)
    if provider:
        filters.append(Event.provider == provider)
    if model:
        filters.append(Event.model == model)
    if team:
        filters.append(Event.team == team)
    if project:
        filters.append(Event.project == project)
    if environment:
        filters.append(Event.environment == environment)
    return filters
