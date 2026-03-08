"""API-key authentication middleware and helpers."""

from __future__ import annotations

import hashlib

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ApiKey, Organization


def hash_api_key(raw_key: str) -> str:
    """Return the SHA-256 hex digest of a raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_current_org(
    x_api_key: str = Header(..., alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> Organization:
    """FastAPI dependency: resolve the API key to an Organization.

    Raises 401 if the key is invalid or revoked.
    """
    key_hash = hash_api_key(x_api_key)

    result = await session.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.revoked_at.is_(None),
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    org_result = await session.execute(
        select(Organization).where(Organization.id == api_key.org_id)
    )
    org = org_result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Organization not found",
        )
    return org
