"""Stripe webhooks and card funding endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.auth import get_current_org
from app.database import get_session
from app.models import (
    CardStatus,
    CardTransaction,
    CardType,
    Event,
    EventType,
    Organization,
    TxnStatus,
    VirtualCard,
)
from app.policy_engine import evaluate
from app.rate_limit import limiter
from app.schemas_cards import FundingRequest, FundingResponse
from app import stripe_service

router = APIRouter()


@router.post("/cards/fund", response_model=FundingResponse)
async def create_funding_session(
    body: FundingRequest,
    org: Organization = Depends(get_current_org),
):
    url = await stripe_service.create_funding_session(body.amount_usd, org.id)
    return FundingResponse(checkout_url=url)


@router.post("/webhooks/stripe")
@limiter.limit("50/minute")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    session: AsyncSession = Depends(get_session),
):
    """Handle Stripe Issuing webhook events.

    No API key auth — verified via Stripe signature.
    """
    payload = await request.body()

    try:
        event = stripe_service.construct_webhook_event(payload, stripe_signature)
    except ValueError:
        logger.warning("Stripe webhook: invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception:
        logger.warning("Stripe webhook: signature verification failed", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "issuing_authorization.request":
        await _handle_authorization(data, session)
    elif event_type == "issuing_transaction.created":
        await _handle_transaction_created(data, session)
    elif event_type == "issuing_transaction.updated":
        await _handle_transaction_updated(data, session)

    return {"received": True}


async def _handle_authorization(data: dict, session: AsyncSession):
    """Evaluate policy engine and approve/decline the authorization."""
    stripe_card_id = data.get("card", {}).get("id", "")
    amount_cents = data.get("pending_request", {}).get("amount", 0)
    amount_usd = Decimal(abs(amount_cents)) / Decimal(100)
    merchant_data = data.get("merchant_data", {})
    merchant_name = merchant_data.get("name", "")
    merchant_mcc = merchant_data.get("category_code", "")

    # Find the card
    result = await session.execute(
        select(VirtualCard).where(VirtualCard.stripe_card_id == stripe_card_id)
    )
    card = result.scalar_one_or_none()

    if not card:
        # Unknown card — decline
        return

    decision = await evaluate(session, card, amount_usd, merchant_name, merchant_mcc)

    if not decision.approved:
        # Record declined transaction
        txn = CardTransaction(
            org_id=card.org_id,
            card_id=card.id,
            stripe_txn_id=data.get("id"),
            amount_usd=amount_usd,
            merchant_name=merchant_name,
            merchant_mcc=merchant_mcc,
            merchant_city=merchant_data.get("city", ""),
            merchant_country=merchant_data.get("country", ""),
            status=TxnStatus.declined,
            decline_reason=decision.reason,
        )
        session.add(txn)
        await session.flush()


async def _handle_transaction_created(data: dict, session: AsyncSession):
    """Record a settled transaction and create an Event for unified reporting."""
    stripe_card_id = data.get("card", "")
    amount_cents = data.get("amount", 0)
    amount_usd = Decimal(abs(amount_cents)) / Decimal(100)
    merchant_data = data.get("merchant_data", {})

    result = await session.execute(
        select(VirtualCard).where(VirtualCard.stripe_card_id == stripe_card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        return

    # Create Event for unified reporting (flows into dashboard via cost_col())
    event = Event(
        org_id=card.org_id,
        idempotency_key=f"stripe_txn_{data.get('id', '')}",
        event_type=EventType.agent_transaction,
        provider="stripe_issuing",
        model="virtual_card",
        timestamp=datetime.now(timezone.utc),
        amount_usd=amount_usd,
        merchant=merchant_data.get("name", ""),
        environment=card.environment,
        team=card.team,
        project=card.project,
        agent_id=card.agent_id,
    )
    session.add(event)
    await session.flush()

    # Create CardTransaction with link to Event
    txn = CardTransaction(
        org_id=card.org_id,
        card_id=card.id,
        event_id=event.id,
        stripe_txn_id=data.get("id"),
        amount_usd=amount_usd,
        merchant_name=merchant_data.get("name", ""),
        merchant_mcc=merchant_data.get("category_code", ""),
        merchant_city=merchant_data.get("city", ""),
        merchant_country=merchant_data.get("country", ""),
        status=TxnStatus.completed,
    )
    session.add(txn)

    # Auto-close single-use cards
    if card.card_type == CardType.single_use:
        card.status = CardStatus.closed
        card.closed_at = datetime.now(timezone.utc)

    await session.flush()


async def _handle_transaction_updated(data: dict, session: AsyncSession):
    """Handle refunds/reversals — update existing transaction."""
    stripe_txn_id = data.get("id", "")
    result = await session.execute(
        select(CardTransaction).where(CardTransaction.stripe_txn_id == stripe_txn_id)
    )
    txn = result.scalar_one_or_none()
    if not txn:
        return

    # Check if this is a reversal
    amount_cents = data.get("amount", 0)
    if amount_cents >= 0:  # Stripe uses negative for charges, positive for credits
        txn.status = TxnStatus.reversed

    await session.flush()
