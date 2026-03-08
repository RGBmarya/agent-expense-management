"""Approval request management for transactions exceeding policy thresholds."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_org
from app.database import get_session
from app.models import ApprovalRequest, ApprovalStatus, Organization
from app.schemas_cards import ApprovalDecisionRequest, ApprovalRequestResponse

router = APIRouter()


@router.get("/approvals", response_model=list[ApprovalRequestResponse])
async def list_approvals(
    status_filter: ApprovalStatus | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    q = select(ApprovalRequest).where(ApprovalRequest.org_id == org.id)
    if status_filter:
        q = q.where(ApprovalRequest.status == status_filter)
    q = q.order_by(ApprovalRequest.requested_at.desc()).limit(limit).offset(offset)
    result = await session.execute(q)
    return result.scalars().all()


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    approval_id: str,
    body: ApprovalDecisionRequest,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.org_id == org.id,
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail="Request already decided")

    approval.status = ApprovalStatus.approved
    approval.decided_at = datetime.now(timezone.utc)
    approval.reason = body.reason
    await session.flush()
    return approval


@router.post("/approvals/{approval_id}/deny", response_model=ApprovalRequestResponse)
async def deny_request(
    approval_id: str,
    body: ApprovalDecisionRequest,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.org_id == org.id,
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(status_code=400, detail="Request already decided")

    approval.status = ApprovalStatus.denied
    approval.decided_at = datetime.now(timezone.utc)
    approval.reason = body.reason
    await session.flush()
    return approval
