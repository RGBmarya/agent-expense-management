"""Integration tests for the approvals API."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest
from uuid import uuid4
from decimal import Decimal

from app.models import ApprovalRequest, ApprovalStatus


class TestApprovalWorkflow:
    async def _create_approval(self, session_factory, org_id, card_id):
        """Helper to insert an approval request directly."""
        async with session_factory() as session:
            approval = ApprovalRequest(
                id=str(uuid4()),
                org_id=org_id,
                card_id=card_id,
                amount_usd=Decimal("500.00"),
                merchant_name="AWS",
                status=ApprovalStatus.pending,
            )
            session.add(approval)
            await session.commit()
            return approval.id

    async def test_list_approvals_empty(self, client):
        resp = await client.get("/v1/approvals")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_approvals_with_data(self, client, session_factory, org):
        # Create a card first
        card_resp = await client.post("/v1/cards", json={"label": "For Approval"})
        card_id = card_resp.json()["id"]

        approval_id = await self._create_approval(session_factory, org.id, card_id)

        resp = await client.get("/v1/approvals")
        assert resp.status_code == 200
        approvals = resp.json()
        assert len(approvals) >= 1

    async def test_approve_request(self, client, session_factory, org):
        card_resp = await client.post("/v1/cards", json={})
        card_id = card_resp.json()["id"]

        approval_id = await self._create_approval(session_factory, org.id, card_id)

        resp = await client.post(f"/v1/approvals/{approval_id}/approve", json={
            "reason": "Looks good",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["reason"] == "Looks good"
        assert data["decided_at"] is not None

    async def test_deny_request(self, client, session_factory, org):
        card_resp = await client.post("/v1/cards", json={})
        card_id = card_resp.json()["id"]

        approval_id = await self._create_approval(session_factory, org.id, card_id)

        resp = await client.post(f"/v1/approvals/{approval_id}/deny", json={
            "reason": "Too expensive",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "denied"

    async def test_cannot_approve_already_decided(self, client, session_factory, org):
        card_resp = await client.post("/v1/cards", json={})
        card_id = card_resp.json()["id"]

        approval_id = await self._create_approval(session_factory, org.id, card_id)

        # Approve first
        await client.post(f"/v1/approvals/{approval_id}/approve", json={})

        # Try to approve again
        resp = await client.post(f"/v1/approvals/{approval_id}/approve", json={})
        assert resp.status_code == 400

    async def test_cannot_deny_already_decided(self, client, session_factory, org):
        card_resp = await client.post("/v1/cards", json={})
        card_id = card_resp.json()["id"]

        approval_id = await self._create_approval(session_factory, org.id, card_id)

        await client.post(f"/v1/approvals/{approval_id}/deny", json={})

        resp = await client.post(f"/v1/approvals/{approval_id}/deny", json={})
        assert resp.status_code == 400

    async def test_approve_nonexistent(self, client):
        resp = await client.post(
            "/v1/approvals/00000000-0000-0000-0000-000000000000/approve",
            json={},
        )
        assert resp.status_code == 404

    async def test_filter_by_status(self, client, session_factory, org):
        card_resp = await client.post("/v1/cards", json={})
        card_id = card_resp.json()["id"]

        await self._create_approval(session_factory, org.id, card_id)

        resp = await client.get("/v1/approvals", params={"status": "pending"})
        assert resp.status_code == 200
        for approval in resp.json():
            assert approval["status"] == "pending"
