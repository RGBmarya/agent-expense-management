"""Tests for API key authentication."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import hashlib
import pytest
from app.auth import hash_api_key


class TestHashApiKey:
    def test_produces_sha256_hex(self):
        result = hash_api_key("test_key")
        assert len(result) == 64  # SHA-256 hex digest
        assert result == hashlib.sha256(b"test_key").hexdigest()

    def test_deterministic(self):
        assert hash_api_key("same_key") == hash_api_key("same_key")

    def test_different_keys_different_hashes(self):
        assert hash_api_key("key_a") != hash_api_key("key_b")

    def test_empty_string(self):
        result = hash_api_key("")
        assert len(result) == 64


class TestGetCurrentOrg:
    async def test_valid_key_returns_org(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_invalid_key_returns_401(self, client):
        resp = await client.get(
            "/v1/alerts",
            headers={"X-API-Key": "invalid_key"},
        )
        assert resp.status_code == 401

    async def test_missing_key_returns_422(self, client):
        from httpx import ASGITransport, AsyncClient
        from app.main import app as _app

        transport = ASGITransport(app=_app)
        async with AsyncClient(transport=transport, base_url="http://test") as bare:
            resp = await bare.get("/v1/alerts")
        assert resp.status_code == 422
