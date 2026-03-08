"""Shared test fixtures for AgentLedger backend."""

import os

# Must set before any app imports
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters!!"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

# Patch SQLite type compiler to handle PostgreSQL-specific types
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base, Organization, ApiKey
from app.auth import hash_api_key
from app.database import get_session
from app.main import app


RAW_API_KEY = "al_test_key_for_testing_purposes"


@pytest_asyncio.fixture()
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def session_factory(test_engine):
    return async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture()
async def session(session_factory):
    async with session_factory() as sess:
        yield sess


@pytest_asyncio.fixture()
async def org(session):
    org = Organization(id=str(uuid4()), name="Test Org")
    session.add(org)
    await session.commit()
    return org


@pytest_asyncio.fixture()
async def api_key(session, org):
    key = ApiKey(
        id=str(uuid4()),
        org_id=org.id,
        key_hash=hash_api_key(RAW_API_KEY),
        label="Test Key",
    )
    session.add(key)
    await session.commit()
    return key


@pytest_asyncio.fixture()
async def client(session_factory, org, api_key):
    async def override_get_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["X-API-Key"] = RAW_API_KEY
        yield c
    app.dependency_overrides.clear()
