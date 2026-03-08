"""API-key management endpoints."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_org, hash_api_key
from app.database import get_session
from app.rate_limit import limiter
from app.models import ApiKey, Organization
from app.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListItem,
    ApiKeyListResponse,
)

router = APIRouter()


@router.post("/auth/keys", response_model=ApiKeyCreateResponse, status_code=201)
@limiter.limit("20/minute")
async def create_api_key(
    request: Request,
    body: ApiKeyCreateRequest,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyCreateResponse:
    """Generate a new API key for the authenticated organization."""
    raw_key = f"al_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(raw_key)

    api_key = ApiKey(
        org_id=org.id,
        key_hash=key_hash,
        label=body.label,
    )
    session.add(api_key)
    await session.flush()

    return ApiKeyCreateResponse(
        id=api_key.id,
        raw_key=raw_key,
        label=api_key.label,
        created_at=api_key.created_at,
    )


@router.get("/auth/keys", response_model=ApiKeyListResponse)
@limiter.limit("20/minute")
async def list_api_keys(
    request: Request,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyListResponse:
    """List all API keys for the organization (hash is never exposed)."""
    result = await session.execute(
        select(ApiKey)
        .where(ApiKey.org_id == org.id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return ApiKeyListResponse(
        keys=[ApiKeyListItem.model_validate(k) for k in keys]
    )


@router.delete("/auth/keys/{key_id}", status_code=204)
@limiter.limit("20/minute")
async def revoke_api_key(
    request: Request,
    key_id: str,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Revoke (soft-delete) an API key by setting revoked_at."""
    from datetime import datetime, timezone

    result = await session.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.org_id == org.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.revoked_at = datetime.now(timezone.utc)
    await session.flush()
