"""Card CRUD, balance, transactions, and lifecycle management."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from app.auth import get_current_org
from app.database import get_session
from app.models import (
    CardStatus,
    CardTransaction,
    CardType,
    Organization,
    SpendProgram,
    TxnStatus,
    VirtualCard,
)
from app.schemas_cards import (
    CardBalanceResponse,
    CardCreate,
    CardResponse,
    CardSensitiveResponse,
    CardTransactionResponse,
    CardUpdate,
)
from app import stripe_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_card(
    card_id: str, org_id: str, session: AsyncSession
) -> VirtualCard:
    result = await session.execute(
        select(VirtualCard).where(
            VirtualCard.id == card_id,
            VirtualCard.org_id == org_id,
        )
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


async def _compute_spend(
    session: AsyncSession,
    card_id: str,
    since: datetime | None = None,
) -> Decimal:
    q = select(
        func.coalesce(func.sum(CardTransaction.amount_usd), Decimal(0))
    ).where(
        CardTransaction.card_id == card_id,
        CardTransaction.status == TxnStatus.completed,
    )
    if since:
        q = q.where(CardTransaction.created_at >= since)
    result = await session.execute(q)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("/cards", response_model=CardResponse, status_code=201)
async def create_card(
    body: CardCreate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    card_kwargs: dict = {
        "org_id": org.id,
        "label": body.label,
        "agent_id": body.agent_id,
        "card_type": body.card_type,
        "spending_limit_usd": body.spending_limit_usd,
        "daily_limit_usd": body.daily_limit_usd,
        "monthly_limit_usd": body.monthly_limit_usd,
        "allowed_mccs": body.allowed_mccs,
        "blocked_mccs": body.blocked_mccs,
        "team": body.team,
        "project": body.project,
        "environment": body.environment,
        "metadata_": body.metadata,
    }

    # If creating from a spend program, apply program defaults
    if body.spend_program_id:
        prog_result = await session.execute(
            select(SpendProgram).where(
                SpendProgram.id == body.spend_program_id,
                SpendProgram.org_id == org.id,
                SpendProgram.is_active.is_(True),
            )
        )
        program = prog_result.scalar_one_or_none()
        if not program:
            raise HTTPException(status_code=404, detail="Spend program not found or inactive")

        card_kwargs["spend_program_id"] = program.id
        card_kwargs["card_type"] = program.card_type
        card_kwargs.setdefault("spending_limit_usd", None)
        if card_kwargs["spending_limit_usd"] is None:
            card_kwargs["spending_limit_usd"] = program.spending_limit_usd
        if card_kwargs["daily_limit_usd"] is None:
            card_kwargs["daily_limit_usd"] = program.daily_limit_usd
        if card_kwargs["monthly_limit_usd"] is None:
            card_kwargs["monthly_limit_usd"] = program.monthly_limit_usd
        if card_kwargs["team"] is None:
            card_kwargs["team"] = program.team
        if card_kwargs["project"] is None:
            card_kwargs["project"] = program.project
        if program.auto_expire_days:
            card_kwargs["expires_at"] = datetime.now(timezone.utc) + timedelta(
                days=program.auto_expire_days
            )

    # Parent card
    if body.parent_card_id:
        parent = await _get_card(body.parent_card_id, org.id, session)
        card_kwargs["parent_card_id"] = parent.id

    # Create Stripe card if configured
    if stripe_service.stripe.api_key:
        try:
            # Find or create cardholder
            stripe_card = await stripe_service.create_card(
                cardholder_id=org.id,  # placeholder — real impl would cache cardholder
                spending_limit_usd=card_kwargs.get("spending_limit_usd"),
                metadata={"org_id": org.id, "agent_id": body.agent_id or ""},
            )
            card_kwargs["stripe_card_id"] = stripe_card.id
            card_kwargs["last4"] = stripe_card.last4
            card_kwargs["exp_month"] = stripe_card.exp_month
            card_kwargs["exp_year"] = stripe_card.exp_year
            card_kwargs["stripe_cardholder_id"] = stripe_card.cardholder
        except Exception:
            logger.warning("Stripe card creation failed; proceeding without", exc_info=True)

    card = VirtualCard(**card_kwargs)
    session.add(card)
    await session.flush()

    # Attach program policy if applicable
    if body.spend_program_id and program and program.policy_id:
        from app.models import CardPolicyLink
        link = CardPolicyLink(card_id=card.id, policy_id=program.policy_id)
        session.add(link)

    await session.flush()
    return card


@router.get("/cards", response_model=list[CardResponse])
async def list_cards(
    status_filter: CardStatus | None = Query(None, alias="status"),
    agent_id: str | None = None,
    team: str | None = None,
    project: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    q = select(VirtualCard).where(VirtualCard.org_id == org.id)
    if status_filter:
        q = q.where(VirtualCard.status == status_filter)
    if agent_id:
        q = q.where(VirtualCard.agent_id == agent_id)
    if team:
        q = q.where(VirtualCard.team == team)
    if project:
        q = q.where(VirtualCard.project == project)
    q = q.order_by(VirtualCard.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(q)
    return result.scalars().all()


@router.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    return await _get_card(card_id, org.id, session)


@router.get("/cards/{card_id}/sensitive", response_model=CardSensitiveResponse)
async def get_card_sensitive(
    card_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(card_id, org.id, session)
    if not card.stripe_card_id:
        raise HTTPException(status_code=400, detail="Card has no Stripe backing")
    details = await stripe_service.get_card_sensitive(card.stripe_card_id)
    return CardSensitiveResponse(
        card_id=card.id,
        number=details["number"],
        cvc=details["cvc"],
        exp_month=details["exp_month"],
        exp_year=details["exp_year"],
    )


_CARD_UPDATABLE_FIELDS = {
    "label", "spending_limit_usd", "daily_limit_usd", "monthly_limit_usd",
    "allowed_mccs", "blocked_mccs", "team", "project",
}


@router.patch("/cards/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: str,
    body: CardUpdate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(card_id, org.id, session)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in _CARD_UPDATABLE_FIELDS:
            setattr(card, field, value)
    await session.flush()
    return card


@router.post("/cards/{card_id}/freeze", response_model=CardResponse)
async def freeze_card(
    card_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(card_id, org.id, session)
    if card.status == CardStatus.closed:
        raise HTTPException(status_code=400, detail="Cannot freeze a closed card")
    card.status = CardStatus.frozen
    if card.stripe_card_id:
        try:
            await stripe_service.update_card(card.stripe_card_id, status="inactive")
        except Exception:
            logger.warning("Stripe freeze failed for card %s", card_id, exc_info=True)
    await session.flush()
    return card


@router.post("/cards/{card_id}/unfreeze", response_model=CardResponse)
async def unfreeze_card(
    card_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(card_id, org.id, session)
    if card.status != CardStatus.frozen:
        raise HTTPException(status_code=400, detail="Card is not frozen")
    card.status = CardStatus.active
    if card.stripe_card_id:
        try:
            await stripe_service.update_card(card.stripe_card_id, status="active")
        except Exception:
            logger.warning("Stripe unfreeze failed for card %s", card_id, exc_info=True)
    await session.flush()
    return card


@router.post("/cards/{card_id}/close", response_model=CardResponse)
async def close_card(
    card_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(card_id, org.id, session)
    if card.status == CardStatus.closed:
        raise HTTPException(status_code=400, detail="Card is already closed")
    card.status = CardStatus.closed
    card.closed_at = datetime.now(timezone.utc)
    if card.stripe_card_id:
        try:
            await stripe_service.cancel_card(card.stripe_card_id)
        except Exception:
            logger.warning("Stripe cancel failed for card %s", card_id, exc_info=True)
    await session.flush()
    return card


@router.get("/cards/{card_id}/balance", response_model=CardBalanceResponse)
async def get_card_balance(
    card_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    card = await _get_card(card_id, org.id, session)
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_spent = await _compute_spend(session, card.id)
    daily_spent = await _compute_spend(session, card.id, since=today)
    monthly_spent = await _compute_spend(session, card.id, since=month_start)

    remaining = None
    if card.spending_limit_usd is not None:
        remaining = max(card.spending_limit_usd - total_spent, Decimal(0))

    return CardBalanceResponse(
        card_id=card.id,
        spending_limit_usd=card.spending_limit_usd,
        total_spent_usd=total_spent,
        remaining_usd=remaining,
        daily_spent_usd=daily_spent,
        daily_limit_usd=card.daily_limit_usd,
        monthly_spent_usd=monthly_spent,
        monthly_limit_usd=card.monthly_limit_usd,
    )


@router.get("/cards/{card_id}/transactions", response_model=list[CardTransactionResponse])
async def get_card_transactions(
    card_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    await _get_card(card_id, org.id, session)  # auth check
    result = await session.execute(
        select(CardTransaction)
        .where(CardTransaction.card_id == card_id)
        .order_by(CardTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.post("/cards/{card_id}/sub-cards", response_model=CardResponse, status_code=201)
async def create_sub_card(
    card_id: str,
    body: CardCreate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    parent = await _get_card(card_id, org.id, session)
    body.parent_card_id = parent.id
    # Inherit team/project from parent if not specified
    if body.team is None:
        body.team = parent.team
    if body.project is None:
        body.project = parent.project
    return await create_card(body, org, session)
