"""CRUD for budget alerts + spend-check endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_org
from app.database import get_session
from app.models import BudgetAlert, Event, Organization, RollupPeriod
from app.schemas import (
    AlertCheckResponse,
    AlertCheckResult,
    BudgetAlertCreate,
    BudgetAlertResponse,
    BudgetAlertUpdate,
)

router = APIRouter()


def _cost_col():
    return func.coalesce(Event.estimated_cost_usd, Event.amount_usd, Decimal(0))


def _period_start(period: RollupPeriod) -> datetime:
    """Return the start of the current period window."""
    now = datetime.now(timezone.utc)
    if period == RollupPeriod.hourly:
        return now.replace(minute=0, second=0, microsecond=0)
    if period == RollupPeriod.daily:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    # monthly
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# ---------------------------------------------------------------------------
# POST /v1/alerts
# ---------------------------------------------------------------------------

@router.post("/alerts", response_model=BudgetAlertResponse, status_code=201)
async def create_alert(
    body: BudgetAlertCreate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> BudgetAlertResponse:
    alert = BudgetAlert(
        org_id=org.id,
        scope=body.scope,
        scope_value=body.scope_value,
        period=body.period,
        threshold_usd=body.threshold_usd,
        notify_channels=body.notify_channels,
        predictive=body.predictive,
    )
    session.add(alert)
    await session.flush()
    return BudgetAlertResponse.model_validate(alert)


# ---------------------------------------------------------------------------
# GET /v1/alerts
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=list[BudgetAlertResponse])
async def list_alerts(
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> list[BudgetAlertResponse]:
    result = await session.execute(
        select(BudgetAlert).where(BudgetAlert.org_id == org.id)
    )
    alerts = result.scalars().all()
    return [BudgetAlertResponse.model_validate(a) for a in alerts]


# ---------------------------------------------------------------------------
# PUT /v1/alerts/{alert_id}
# ---------------------------------------------------------------------------

@router.put("/alerts/{alert_id}", response_model=BudgetAlertResponse)
async def update_alert(
    alert_id: str,
    body: BudgetAlertUpdate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> BudgetAlertResponse:
    result = await session.execute(
        select(BudgetAlert).where(
            BudgetAlert.id == alert_id,
            BudgetAlert.org_id == org.id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    await session.flush()
    return BudgetAlertResponse.model_validate(alert)


# ---------------------------------------------------------------------------
# DELETE /v1/alerts/{alert_id}
# ---------------------------------------------------------------------------

@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        select(BudgetAlert).where(
            BudgetAlert.id == alert_id,
            BudgetAlert.org_id == org.id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    await session.delete(alert)
    await session.flush()


# ---------------------------------------------------------------------------
# GET /v1/alerts/check
# ---------------------------------------------------------------------------

@router.get("/alerts/check", response_model=AlertCheckResponse)
async def check_alerts(
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> AlertCheckResponse:
    """Check current spend against all configured alert thresholds."""
    result = await session.execute(
        select(BudgetAlert).where(BudgetAlert.org_id == org.id)
    )
    alerts = result.scalars().all()

    results: list[AlertCheckResult] = []
    for alert in alerts:
        ps = _period_start(alert.period)

        # Build filters for scope
        filters = [
            Event.org_id == org.id,
            Event.timestamp >= ps,
        ]
        if alert.scope == "provider":
            filters.append(Event.provider == alert.scope_value)
        elif alert.scope == "team":
            filters.append(Event.team == alert.scope_value)
        elif alert.scope == "project":
            filters.append(Event.project == alert.scope_value)
        elif alert.scope == "model":
            filters.append(Event.model == alert.scope_value)
        # scope == "org" means all events for the org

        spend_result = await session.execute(
            select(func.coalesce(func.sum(_cost_col()), Decimal(0))).where(*filters)
        )
        current_spend: Decimal = spend_result.scalar_one()

        threshold = alert.threshold_usd
        pct = float(current_spend / threshold * 100) if threshold else 0.0
        triggered = current_spend >= threshold

        # Update last_triggered_at if newly triggered
        if triggered and alert.last_triggered_at is None:
            alert.last_triggered_at = datetime.now(timezone.utc)

        results.append(
            AlertCheckResult(
                alert_id=alert.id,
                scope=alert.scope,
                scope_value=alert.scope_value,
                threshold_usd=threshold,
                current_spend_usd=current_spend,
                pct_used=round(pct, 2),
                triggered=triggered,
            )
        )

    return AlertCheckResponse(results=results)
