"""Reporting endpoints – monthly report, CSV export, invoice reconciliation."""

from __future__ import annotations

import asyncio
import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_org
from app.database import get_session
from app.models import Event, Organization
from app.queries import build_event_filters, cost_col, month_to_range
from app.rate_limit import limiter
from app.schemas import (
    InvoiceReconciliationRequest,
    InvoiceReconciliationResponse,
    MonthlyReportResponse,
    MonthlyReportRow,
    ReconciliationRow,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /v1/reports/monthly
# ---------------------------------------------------------------------------

@router.get("/reports/monthly", response_model=MonthlyReportResponse)
async def monthly_report(
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
) -> MonthlyReportResponse:
    """Monthly cost report grouped by team, project, and provider."""
    start, end = month_to_range(month)

    stmt = (
        select(
            func.coalesce(Event.team, "unassigned").label("team"),
            func.coalesce(Event.project, "unassigned").label("project"),
            func.coalesce(Event.provider, "unknown").label("provider"),
            func.coalesce(func.sum(cost_col()), Decimal(0)).label("total_cost_usd"),
            func.count().label("request_count"),
        )
        .where(
            Event.org_id == org.id,
            Event.timestamp >= start,
            Event.timestamp < end,
        )
        .group_by(Event.team, Event.project, Event.provider)
        .order_by(func.sum(cost_col()).desc())
    )
    rows = (await session.execute(stmt)).all()

    report_rows = [
        MonthlyReportRow(
            month=month,
            team=r.team,
            project=r.project,
            provider=r.provider,
            total_cost_usd=r.total_cost_usd,
            request_count=r.request_count,
        )
        for r in rows
    ]
    grand_total = sum(r.total_cost_usd for r in report_rows) if report_rows else Decimal(0)

    return MonthlyReportResponse(rows=report_rows, grand_total_usd=grand_total)


# ---------------------------------------------------------------------------
# GET /v1/reports/export
# ---------------------------------------------------------------------------

CSV_HEADER = [
    "id", "timestamp", "event_type", "provider", "model",
    "input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens",
    "latency_ms", "amount_usd", "estimated_cost_usd",
    "team", "project", "environment", "agent_id",
]


@router.get("/reports/export")
@limiter.limit("10/minute")
async def export_csv(
    request: Request,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
) -> StreamingResponse:
    """CSV export of filtered event data (streamed)."""
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

    stmt = select(Event).where(*filters).order_by(Event.timestamp.desc()).limit(50_000)
    result = await session.execute(stmt)

    async def generate_csv() -> AsyncIterator[str]:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CSV_HEADER)
        yield buf.getvalue()

        for ev in result.scalars().yield_per(500):
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                ev.id,
                ev.timestamp.isoformat() if ev.timestamp else "",
                ev.event_type.value if ev.event_type else "",
                ev.provider,
                ev.model,
                ev.input_tokens,
                ev.output_tokens,
                ev.cached_tokens,
                ev.reasoning_tokens,
                ev.latency_ms,
                str(ev.amount_usd) if ev.amount_usd is not None else "",
                str(ev.estimated_cost_usd) if ev.estimated_cost_usd is not None else "",
                ev.team or "",
                ev.project or "",
                ev.environment or "",
                ev.agent_id or "",
            ])
            yield buf.getvalue()

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=events_export.csv"},
    )


# ---------------------------------------------------------------------------
# GET /v1/reports/invoice-reconciliation
# ---------------------------------------------------------------------------

@router.post("/reports/invoice-reconciliation", response_model=InvoiceReconciliationResponse)
async def invoice_reconciliation(
    body: InvoiceReconciliationRequest,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> InvoiceReconciliationResponse:
    """Compare tracked spend against manually provided invoice amounts."""
    start, end = month_to_range(body.month)

    # Get tracked spend grouped by provider
    stmt = (
        select(
            Event.provider,
            func.coalesce(func.sum(cost_col()), Decimal(0)).label("tracked_usd"),
        )
        .where(
            Event.org_id == org.id,
            Event.timestamp >= start,
            Event.timestamp < end,
        )
        .group_by(Event.provider)
    )
    rows = (await session.execute(stmt)).all()
    tracked_map: dict[str, Decimal] = {r.provider: r.tracked_usd for r in rows}

    reconciliation: list[ReconciliationRow] = []
    for item in body.line_items:
        tracked = tracked_map.get(item.provider, Decimal(0))
        diff = tracked - item.invoice_amount_usd
        pct = (
            float(diff / item.invoice_amount_usd * 100)
            if item.invoice_amount_usd
            else 0.0
        )
        reconciliation.append(
            ReconciliationRow(
                provider=item.provider,
                tracked_usd=tracked,
                invoice_usd=item.invoice_amount_usd,
                difference_usd=diff,
                pct_difference=round(pct, 2),
            )
        )

    return InvoiceReconciliationResponse(month=body.month, rows=reconciliation)
