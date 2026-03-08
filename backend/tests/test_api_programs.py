"""Integration tests for the spend programs API."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest


class TestProgramCRUD:
    async def test_create_program(self, client):
        resp = await client.post("/v1/programs", json={
            "name": "Engineering Cards",
            "spending_limit_usd": "5000",
            "daily_limit_usd": "500",
            "monthly_limit_usd": "5000",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Engineering Cards"
        assert data["is_active"] is True

    async def test_list_programs(self, client):
        await client.post("/v1/programs", json={"name": "Program 1"})
        await client.post("/v1/programs", json={"name": "Program 2"})

        resp = await client.get("/v1/programs")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_update_program(self, client):
        create_resp = await client.post("/v1/programs", json={"name": "Old Name"})
        program_id = create_resp.json()["id"]

        resp = await client.patch(f"/v1/programs/{program_id}", json={
            "name": "New Name",
            "is_active": False,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["is_active"] is False


class TestProgramCardIssuance:
    async def test_issue_card_from_program(self, client):
        prog_resp = await client.post("/v1/programs", json={
            "name": "Agent Cards",
            "spending_limit_usd": "1000",
            "team": "ml-team",
            "auto_expire_days": 30,
        })
        program_id = prog_resp.json()["id"]

        resp = await client.post(f"/v1/programs/{program_id}/issue", json={
            "agent_id": "agent-001",
            "label": "Agent 001 Card",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_id"] == "agent-001"
        assert data["team"] == "ml-team"
        assert data["spend_program_id"] == program_id
        assert data["expires_at"] is not None

    async def test_issue_card_from_inactive_program(self, client):
        prog_resp = await client.post("/v1/programs", json={"name": "Inactive"})
        program_id = prog_resp.json()["id"]

        # Deactivate
        await client.patch(f"/v1/programs/{program_id}", json={"is_active": False})

        resp = await client.post(f"/v1/programs/{program_id}/issue", json={})
        assert resp.status_code == 400

    async def test_issue_card_nonexistent_program(self, client):
        resp = await client.post(
            "/v1/programs/00000000-0000-0000-0000-000000000000/issue",
            json={},
        )
        assert resp.status_code == 404

    async def test_issued_card_inherits_limits(self, client):
        prog_resp = await client.post("/v1/programs", json={
            "name": "With Limits",
            "spending_limit_usd": "2000",
            "daily_limit_usd": "200",
            "monthly_limit_usd": "2000",
            "card_type": "single_use",
        })
        program_id = prog_resp.json()["id"]

        resp = await client.post(f"/v1/programs/{program_id}/issue", json={})
        data = resp.json()
        assert float(data["spending_limit_usd"]) == 2000.0
        assert float(data["daily_limit_usd"]) == 200.0
        assert data["card_type"] == "single_use"
