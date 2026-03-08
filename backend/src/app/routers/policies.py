"""Spend policy CRUD and card attachment management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_org
from app.database import get_session
from app.models import CardPolicyLink, Organization, SpendPolicy, VirtualCard
from app.schemas_cards import (
    PolicyAttachRequest,
    SpendPolicyCreate,
    SpendPolicyResponse,
    SpendPolicyUpdate,
)

router = APIRouter()


async def _get_policy(
    policy_id: str, org_id: str, session: AsyncSession
) -> SpendPolicy:
    result = await session.execute(
        select(SpendPolicy).where(
            SpendPolicy.id == policy_id,
            SpendPolicy.org_id == org_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("/policies", response_model=SpendPolicyResponse, status_code=201)
async def create_policy(
    body: SpendPolicyCreate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    policy = SpendPolicy(
        org_id=org.id,
        **body.model_dump(),
    )
    session.add(policy)
    await session.flush()
    return policy


@router.get("/policies", response_model=list[SpendPolicyResponse])
async def list_policies(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SpendPolicy)
        .where(SpendPolicy.org_id == org.id)
        .order_by(SpendPolicy.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/policies/{policy_id}", response_model=SpendPolicyResponse)
async def get_policy(
    policy_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    return await _get_policy(policy_id, org.id, session)


_POLICY_UPDATABLE_FIELDS = {
    "name", "scope", "max_transaction_usd", "daily_limit_usd", "monthly_limit_usd",
    "allowed_mccs", "blocked_mccs", "blocked_merchants", "allowed_merchants",
    "require_approval_above_usd", "auto_close_after_first_use", "auto_expire_days",
    "is_default",
}


@router.patch("/policies/{policy_id}", response_model=SpendPolicyResponse)
async def update_policy(
    policy_id: str,
    body: SpendPolicyUpdate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    policy = await _get_policy(policy_id, org.id, session)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in _POLICY_UPDATABLE_FIELDS:
            setattr(policy, field, value)
    await session.flush()
    return policy


@router.delete("/policies/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    policy = await _get_policy(policy_id, org.id, session)
    # Detach from all cards first
    await session.execute(
        delete(CardPolicyLink).where(CardPolicyLink.policy_id == policy.id)
    )
    await session.delete(policy)
    await session.flush()


@router.post("/policies/{policy_id}/attach", status_code=200)
async def attach_policy(
    policy_id: str,
    body: PolicyAttachRequest,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    policy = await _get_policy(policy_id, org.id, session)

    # Verify all cards belong to the org
    for card_id in body.card_ids:
        result = await session.execute(
            select(VirtualCard).where(
                VirtualCard.id == card_id,
                VirtualCard.org_id == org.id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Card {card_id} not found")

    # Insert links (ignore duplicates)
    for card_id in body.card_ids:
        existing = await session.execute(
            select(CardPolicyLink).where(
                CardPolicyLink.card_id == card_id,
                CardPolicyLink.policy_id == policy.id,
            )
        )
        if not existing.scalar_one_or_none():
            session.add(CardPolicyLink(card_id=card_id, policy_id=policy.id))

    await session.flush()
    return {"attached": len(body.card_ids)}


@router.post("/policies/{policy_id}/detach", status_code=200)
async def detach_policy(
    policy_id: str,
    body: PolicyAttachRequest,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    await _get_policy(policy_id, org.id, session)  # auth check
    await session.execute(
        delete(CardPolicyLink).where(
            CardPolicyLink.policy_id == policy_id,
            CardPolicyLink.card_id.in_(body.card_ids),
        )
    )
    await session.flush()
    return {"detached": len(body.card_ids)}
