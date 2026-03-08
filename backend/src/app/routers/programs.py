"""Spend program CRUD and card issuance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_org
from app.database import get_session
from app.models import (
    CardPolicyLink,
    Organization,
    SpendProgram,
    VirtualCard,
)
from app.schemas_cards import (
    CardResponse,
    ProgramIssueRequest,
    SpendProgramCreate,
    SpendProgramResponse,
    SpendProgramUpdate,
)

router = APIRouter()


async def _get_program(
    program_id: str, org_id: str, session: AsyncSession
) -> SpendProgram:
    result = await session.execute(
        select(SpendProgram).where(
            SpendProgram.id == program_id,
            SpendProgram.org_id == org_id,
        )
    )
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Spend program not found")
    return program


@router.post("/programs", response_model=SpendProgramResponse, status_code=201)
async def create_program(
    body: SpendProgramCreate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    program = SpendProgram(
        org_id=org.id,
        name=body.name,
        card_type=body.card_type,
        spending_limit_usd=body.spending_limit_usd,
        daily_limit_usd=body.daily_limit_usd,
        monthly_limit_usd=body.monthly_limit_usd,
        policy_id=body.policy_id,
        team=body.team,
        project=body.project,
        auto_expire_days=body.auto_expire_days,
        metadata_=body.metadata,
    )
    session.add(program)
    await session.flush()
    return program


@router.get("/programs", response_model=list[SpendProgramResponse])
async def list_programs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SpendProgram)
        .where(SpendProgram.org_id == org.id)
        .order_by(SpendProgram.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


_PROGRAM_UPDATABLE_FIELDS = {
    "name", "card_type", "spending_limit_usd", "daily_limit_usd", "monthly_limit_usd",
    "policy_id", "team", "project", "auto_expire_days", "is_active",
}


@router.patch("/programs/{program_id}", response_model=SpendProgramResponse)
async def update_program(
    program_id: str,
    body: SpendProgramUpdate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    program = await _get_program(program_id, org.id, session)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in _PROGRAM_UPDATABLE_FIELDS:
            setattr(program, field, value)
    await session.flush()
    return program


@router.post("/programs/{program_id}/issue", response_model=CardResponse, status_code=201)
async def issue_card_from_program(
    program_id: str,
    body: ProgramIssueRequest,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    program = await _get_program(program_id, org.id, session)
    if not program.is_active:
        raise HTTPException(status_code=400, detail="Spend program is inactive")

    expires_at = None
    if program.auto_expire_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=program.auto_expire_days)

    card = VirtualCard(
        org_id=org.id,
        agent_id=body.agent_id,
        label=body.label,
        card_type=program.card_type,
        spending_limit_usd=program.spending_limit_usd,
        daily_limit_usd=program.daily_limit_usd,
        monthly_limit_usd=program.monthly_limit_usd,
        team=program.team,
        project=program.project,
        environment=body.environment,
        spend_program_id=program.id,
        expires_at=expires_at,
    )
    session.add(card)
    await session.flush()

    # Attach program policy
    if program.policy_id:
        link = CardPolicyLink(card_id=card.id, policy_id=program.policy_id)
        session.add(link)
        await session.flush()

    return card
