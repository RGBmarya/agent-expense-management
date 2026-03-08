"""Integration tests for the spend policies API."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest


class TestPolicyCRUD:
    async def test_create_policy(self, client):
        resp = await client.post("/v1/policies", json={
            "name": "Strict Policy",
            "max_transaction_usd": "500",
            "daily_limit_usd": "1000",
            "monthly_limit_usd": "5000",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Strict Policy"
        assert data["scope"] == "card"

    async def test_create_policy_with_mccs(self, client):
        resp = await client.post("/v1/policies", json={
            "name": "MCC Policy",
            "allowed_mccs": ["5411", "5812"],
            "blocked_merchants": ["Casino"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["allowed_mccs"] == ["5411", "5812"]

    async def test_list_policies(self, client):
        await client.post("/v1/policies", json={"name": "Policy 1"})
        await client.post("/v1/policies", json={"name": "Policy 2"})

        resp = await client.get("/v1/policies")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_get_policy(self, client):
        create_resp = await client.post("/v1/policies", json={"name": "Get Me"})
        policy_id = create_resp.json()["id"]

        resp = await client.get(f"/v1/policies/{policy_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Me"

    async def test_update_policy(self, client):
        create_resp = await client.post("/v1/policies", json={"name": "Old Name"})
        policy_id = create_resp.json()["id"]

        resp = await client.patch(f"/v1/policies/{policy_id}", json={
            "name": "New Name",
            "max_transaction_usd": "250",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    async def test_delete_policy(self, client):
        create_resp = await client.post("/v1/policies", json={"name": "Delete Me"})
        policy_id = create_resp.json()["id"]

        resp = await client.delete(f"/v1/policies/{policy_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await client.get(f"/v1/policies/{policy_id}")
        assert resp.status_code == 404

    async def test_get_nonexistent_policy(self, client):
        resp = await client.get("/v1/policies/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestPolicyAttachment:
    async def test_attach_policy_to_card(self, client):
        # Create policy and card
        policy_resp = await client.post("/v1/policies", json={"name": "Attach Me"})
        policy_id = policy_resp.json()["id"]

        card_resp = await client.post("/v1/cards", json={"label": "Card A"})
        card_id = card_resp.json()["id"]

        resp = await client.post(f"/v1/policies/{policy_id}/attach", json={
            "card_ids": [card_id],
        })
        assert resp.status_code == 200
        assert resp.json()["attached"] == 1

    async def test_attach_idempotent(self, client):
        policy_resp = await client.post("/v1/policies", json={"name": "Idempotent"})
        policy_id = policy_resp.json()["id"]

        card_resp = await client.post("/v1/cards", json={})
        card_id = card_resp.json()["id"]

        # Attach twice
        await client.post(f"/v1/policies/{policy_id}/attach", json={"card_ids": [card_id]})
        resp = await client.post(f"/v1/policies/{policy_id}/attach", json={"card_ids": [card_id]})
        assert resp.status_code == 200

    async def test_detach_policy(self, client):
        policy_resp = await client.post("/v1/policies", json={"name": "Detach Me"})
        policy_id = policy_resp.json()["id"]

        card_resp = await client.post("/v1/cards", json={})
        card_id = card_resp.json()["id"]

        await client.post(f"/v1/policies/{policy_id}/attach", json={"card_ids": [card_id]})
        resp = await client.post(f"/v1/policies/{policy_id}/detach", json={"card_ids": [card_id]})
        assert resp.status_code == 200

    async def test_attach_nonexistent_card(self, client):
        policy_resp = await client.post("/v1/policies", json={"name": "No Card"})
        policy_id = policy_resp.json()["id"]

        resp = await client.post(f"/v1/policies/{policy_id}/attach", json={
            "card_ids": ["00000000-0000-0000-0000-000000000000"],
        })
        assert resp.status_code == 404
