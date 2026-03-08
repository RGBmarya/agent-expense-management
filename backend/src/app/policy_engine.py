"""Cascading policy evaluation engine for card transactions.

Called during Stripe issuing_authorization.request webhook.
Must respond in <2 seconds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ApprovalRequest,
    ApprovalStatus,
    CardStatus,
    CardTransaction,
    SpendPolicy,
    TxnStatus,
    VirtualCard,
)


@dataclass
class PolicyDecision:
    approved: bool
    reason: str


async def _daily_spend(session: AsyncSession, card_id: str) -> Decimal:
    """Sum of completed transactions for the card today (UTC)."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.coalesce(func.sum(CardTransaction.amount_usd), Decimal(0)))
        .where(
            CardTransaction.card_id == card_id,
            CardTransaction.status == TxnStatus.completed,
            CardTransaction.created_at >= today,
        )
    )
    return result.scalar_one()


async def _monthly_spend(session: AsyncSession, card_id: str) -> Decimal:
    """Sum of completed transactions for the card this month (UTC)."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.coalesce(func.sum(CardTransaction.amount_usd), Decimal(0)))
        .where(
            CardTransaction.card_id == card_id,
            CardTransaction.status == TxnStatus.completed,
            CardTransaction.created_at >= month_start,
        )
    )
    return result.scalar_one()


async def _total_spend(session: AsyncSession, card_id: str) -> Decimal:
    """Sum of all completed transactions for the card."""
    result = await session.execute(
        select(func.coalesce(func.sum(CardTransaction.amount_usd), Decimal(0)))
        .where(
            CardTransaction.card_id == card_id,
            CardTransaction.status == TxnStatus.completed,
        )
    )
    return result.scalar_one()


def _check_mcc_lists(
    mcc: str,
    allowed_mccs: list[str] | None,
    blocked_mccs: list[str] | None,
) -> str | None:
    """Check MCC against allowed/blocked lists. Returns decline reason or None."""
    if allowed_mccs and mcc not in allowed_mccs:
        return f"MCC {mcc} not in allowed list"
    if blocked_mccs and mcc in blocked_mccs:
        return f"MCC {mcc} is blocked"
    return None


def _check_merchant_lists(
    merchant_name: str,
    allowed_merchants: list[str] | None,
    blocked_merchants: list[str] | None,
) -> str | None:
    """Check merchant against allowed/blocked lists. Returns decline reason or None."""
    normalized = merchant_name.strip().lower()
    if allowed_merchants:
        if not any(normalized == m.strip().lower() for m in allowed_merchants):
            return f"Merchant '{merchant_name}' not in allowed list"
    if blocked_merchants:
        if any(normalized == m.strip().lower() for m in blocked_merchants):
            return f"Merchant '{merchant_name}' is blocked"
    return None


async def evaluate(
    session: AsyncSession,
    card: VirtualCard,
    amount: Decimal,
    merchant_name: str,
    merchant_mcc: str,
) -> PolicyDecision:
    """Evaluate whether a transaction should be approved.

    Cascade (all must pass):
    1. Card status check
    2. Card-level controls (spending_limit, daily_limit, monthly_limit, MCCs)
    3. Attached policies
    4. Org default policy
    5. Parent card constraints
    6. Approval threshold check
    """
    # 1. Card status
    if card.status == CardStatus.frozen:
        return PolicyDecision(False, "Card is frozen")
    if card.status == CardStatus.closed:
        return PolicyDecision(False, "Card is closed")
    if card.status != CardStatus.active:
        return PolicyDecision(False, f"Card status is {card.status.value}")

    # Check expiration
    if card.expires_at and datetime.now(timezone.utc) > card.expires_at:
        return PolicyDecision(False, "Card has expired")

    # 2. Card-level controls
    if card.spending_limit_usd is not None:
        total = await _total_spend(session, card.id)
        if total + amount > card.spending_limit_usd:
            return PolicyDecision(False, "Exceeds card spending limit")

    if card.daily_limit_usd is not None:
        daily = await _daily_spend(session, card.id)
        if daily + amount > card.daily_limit_usd:
            return PolicyDecision(False, "Exceeds daily limit")

    if card.monthly_limit_usd is not None:
        monthly = await _monthly_spend(session, card.id)
        if monthly + amount > card.monthly_limit_usd:
            return PolicyDecision(False, "Exceeds monthly limit")

    if merchant_mcc:
        mcc_reason = _check_mcc_lists(merchant_mcc, card.allowed_mccs, card.blocked_mccs)
        if mcc_reason:
            return PolicyDecision(False, mcc_reason)

    # 3. Attached policies — load eagerly
    result = await session.execute(
        select(VirtualCard)
        .where(VirtualCard.id == card.id)
        .options(selectinload(VirtualCard.policies))
    )
    card_with_policies = result.scalar_one()
    policies: list[SpendPolicy] = list(card_with_policies.policies)

    # 4. Org default policy — add if not already attached
    default_result = await session.execute(
        select(SpendPolicy).where(
            SpendPolicy.org_id == card.org_id,
            SpendPolicy.is_default.is_(True),
        )
    )
    default_policy = default_result.scalar_one_or_none()
    if default_policy and default_policy.id not in {p.id for p in policies}:
        policies.append(default_policy)

    # Track lowest approval threshold
    approval_threshold: Decimal | None = None

    for policy in policies:
        if policy.max_transaction_usd is not None and amount > policy.max_transaction_usd:
            return PolicyDecision(False, f"Exceeds max transaction (policy: {policy.name})")

        if policy.daily_limit_usd is not None:
            daily = await _daily_spend(session, card.id)
            if daily + amount > policy.daily_limit_usd:
                return PolicyDecision(False, f"Exceeds daily limit (policy: {policy.name})")

        if policy.monthly_limit_usd is not None:
            monthly = await _monthly_spend(session, card.id)
            if monthly + amount > policy.monthly_limit_usd:
                return PolicyDecision(False, f"Exceeds monthly limit (policy: {policy.name})")

        if merchant_mcc:
            mcc_reason = _check_mcc_lists(merchant_mcc, policy.allowed_mccs, policy.blocked_mccs)
            if mcc_reason:
                return PolicyDecision(False, f"{mcc_reason} (policy: {policy.name})")

        if merchant_name:
            merchant_reason = _check_merchant_lists(
                merchant_name, policy.allowed_merchants, policy.blocked_merchants
            )
            if merchant_reason:
                return PolicyDecision(False, f"{merchant_reason} (policy: {policy.name})")

        if policy.require_approval_above_usd is not None:
            if approval_threshold is None or policy.require_approval_above_usd < approval_threshold:
                approval_threshold = policy.require_approval_above_usd

    # 5. Parent card constraints
    if card.parent_card_id:
        parent_result = await session.execute(
            select(VirtualCard).where(VirtualCard.id == card.parent_card_id)
        )
        parent = parent_result.scalar_one_or_none()
        if parent and parent.spending_limit_usd is not None:
            parent_total = await _total_spend(session, parent.id)
            # Sub-card spend also counts against parent
            sub_total = await _total_spend(session, card.id)
            if parent_total + sub_total + amount > parent.spending_limit_usd:
                return PolicyDecision(False, "Exceeds parent card spending limit")

    # 6. Approval threshold
    if approval_threshold is not None and amount > approval_threshold:
        # Create an approval request
        approval = ApprovalRequest(
            org_id=card.org_id,
            card_id=card.id,
            amount_usd=amount,
            merchant_name=merchant_name,
            status=ApprovalStatus.pending,
        )
        session.add(approval)
        await session.flush()
        return PolicyDecision(False, "pending_approval")

    return PolicyDecision(True, "approved")
