"""Integration tests for the API key management endpoints."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest


class TestApiKeyManagement:
    async def test_create_api_key(self, client):
        resp = await client.post("/v1/auth/keys", json={
            "label": "Production Key",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["label"] == "Production Key"
        assert data["raw_key"].startswith("al_")
        assert "id" in data
        assert "created_at" in data

    async def test_create_key_default_label(self, client):
        resp = await client.post("/v1/auth/keys", json={})
        assert resp.status_code == 201
        assert resp.json()["label"] == ""

    async def test_list_api_keys(self, client):
        # Create a new key
        await client.post("/v1/auth/keys", json={"label": "Key 1"})

        resp = await client.get("/v1/auth/keys")
        assert resp.status_code == 200
        data = resp.json()
        # Should include the fixture key + newly created key
        assert len(data["keys"]) >= 2

    async def test_list_keys_does_not_expose_hash(self, client):
        resp = await client.get("/v1/auth/keys")
        assert resp.status_code == 200
        for key in resp.json()["keys"]:
            assert "key_hash" not in key
            assert "raw_key" not in key

    async def test_revoke_api_key(self, client):
        # Create a key to revoke
        create_resp = await client.post("/v1/auth/keys", json={"label": "Revoke Me"})
        key_id = create_resp.json()["id"]

        resp = await client.delete(f"/v1/auth/keys/{key_id}")
        assert resp.status_code == 204

    async def test_revoke_nonexistent_key(self, client):
        resp = await client.delete("/v1/auth/keys/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_revoked_key_cannot_authenticate(self, client):
        # Create and get a new key
        create_resp = await client.post("/v1/auth/keys", json={"label": "Temp Key"})
        raw_key = create_resp.json()["raw_key"]
        key_id = create_resp.json()["id"]

        # Revoke it
        await client.delete(f"/v1/auth/keys/{key_id}")

        # Try using the revoked key
        resp = await client.get(
            "/v1/auth/keys",
            headers={"X-API-Key": raw_key},
        )
        assert resp.status_code == 401
