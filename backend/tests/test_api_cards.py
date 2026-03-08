"""Integration tests for the cards API."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest


class TestCardCRUD:
    async def test_create_card(self, client):
        resp = await client.post("/v1/cards", json={
            "label": "Test Card",
            "card_type": "multi_use",
            "spending_limit_usd": "1000.00",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["label"] == "Test Card"
        assert data["status"] == "active"
        assert data["card_type"] == "multi_use"

    async def test_create_minimal_card(self, client):
        resp = await client.post("/v1/cards", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "active"

    async def test_list_cards(self, client):
        # Create two cards
        await client.post("/v1/cards", json={"label": "Card 1"})
        await client.post("/v1/cards", json={"label": "Card 2"})

        resp = await client.get("/v1/cards")
        assert resp.status_code == 200
        cards = resp.json()
        assert len(cards) >= 2

    async def test_list_cards_filter_by_status(self, client):
        await client.post("/v1/cards", json={"label": "Active Card"})
        resp = await client.get("/v1/cards", params={"status": "active"})
        assert resp.status_code == 200

    async def test_get_card(self, client):
        create_resp = await client.post("/v1/cards", json={"label": "Get Me"})
        card_id = create_resp.json()["id"]

        resp = await client.get(f"/v1/cards/{card_id}")
        assert resp.status_code == 200
        assert resp.json()["label"] == "Get Me"

    async def test_get_nonexistent_card(self, client):
        resp = await client.get("/v1/cards/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_update_card(self, client):
        create_resp = await client.post("/v1/cards", json={"label": "Old Label"})
        card_id = create_resp.json()["id"]

        resp = await client.patch(f"/v1/cards/{card_id}", json={
            "label": "New Label",
            "spending_limit_usd": "500.00",
        })
        assert resp.status_code == 200
        assert resp.json()["label"] == "New Label"


class TestCardLifecycle:
    async def test_freeze_card(self, client):
        create_resp = await client.post("/v1/cards", json={"label": "Freeze Me"})
        card_id = create_resp.json()["id"]

        resp = await client.post(f"/v1/cards/{card_id}/freeze")
        assert resp.status_code == 200
        assert resp.json()["status"] == "frozen"

    async def test_unfreeze_card(self, client):
        create_resp = await client.post("/v1/cards", json={})
        card_id = create_resp.json()["id"]

        await client.post(f"/v1/cards/{card_id}/freeze")
        resp = await client.post(f"/v1/cards/{card_id}/unfreeze")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    async def test_unfreeze_non_frozen_card(self, client):
        create_resp = await client.post("/v1/cards", json={})
        card_id = create_resp.json()["id"]

        resp = await client.post(f"/v1/cards/{card_id}/unfreeze")
        assert resp.status_code == 400

    async def test_close_card(self, client):
        create_resp = await client.post("/v1/cards", json={})
        card_id = create_resp.json()["id"]

        resp = await client.post(f"/v1/cards/{card_id}/close")
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"
        assert resp.json()["closed_at"] is not None

    async def test_close_already_closed_card(self, client):
        create_resp = await client.post("/v1/cards", json={})
        card_id = create_resp.json()["id"]

        await client.post(f"/v1/cards/{card_id}/close")
        resp = await client.post(f"/v1/cards/{card_id}/close")
        assert resp.status_code == 400

    async def test_freeze_closed_card(self, client):
        create_resp = await client.post("/v1/cards", json={})
        card_id = create_resp.json()["id"]

        await client.post(f"/v1/cards/{card_id}/close")
        resp = await client.post(f"/v1/cards/{card_id}/freeze")
        assert resp.status_code == 400


class TestCardBalance:
    async def test_balance_no_transactions(self, client):
        create_resp = await client.post("/v1/cards", json={
            "spending_limit_usd": "1000.00",
        })
        card_id = create_resp.json()["id"]

        resp = await client.get(f"/v1/cards/{card_id}/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert float(data["total_spent_usd"]) == 0.0
        assert float(data["remaining_usd"]) == 1000.0

    async def test_balance_no_limit(self, client):
        create_resp = await client.post("/v1/cards", json={})
        card_id = create_resp.json()["id"]

        resp = await client.get(f"/v1/cards/{card_id}/balance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["remaining_usd"] is None


class TestCardTransactions:
    async def test_transactions_empty(self, client):
        create_resp = await client.post("/v1/cards", json={})
        card_id = create_resp.json()["id"]

        resp = await client.get(f"/v1/cards/{card_id}/transactions")
        assert resp.status_code == 200
        assert resp.json() == []


class TestSubCards:
    async def test_create_sub_card(self, client):
        parent_resp = await client.post("/v1/cards", json={
            "label": "Parent",
            "team": "ml-team",
        })
        parent_id = parent_resp.json()["id"]

        resp = await client.post(f"/v1/cards/{parent_id}/sub-cards", json={
            "label": "Child",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["parent_card_id"] == parent_id
        assert data["team"] == "ml-team"  # inherited from parent
