"""Integration tests for the budget alerts API."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest


class TestAlertCRUD:
    async def test_create_alert(self, client):
        resp = await client.post("/v1/alerts", json={
            "scope": "org",
            "period": "monthly",
            "threshold_usd": "10000.00",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["scope"] == "org"
        assert float(data["threshold_usd"]) == 10000.0
        assert data["predictive"] is False

    async def test_create_scoped_alert(self, client):
        resp = await client.post("/v1/alerts", json={
            "scope": "team",
            "scope_value": "ml-team",
            "period": "daily",
            "threshold_usd": "500",
            "notify_channels": {"slack": "#alerts"},
            "predictive": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["scope_value"] == "ml-team"
        assert data["predictive"] is True

    async def test_list_alerts(self, client):
        await client.post("/v1/alerts", json={
            "scope": "org",
            "period": "monthly",
            "threshold_usd": "5000",
        })
        resp = await client.get("/v1/alerts")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_alert(self, client):
        create_resp = await client.post("/v1/alerts", json={
            "scope": "org",
            "period": "monthly",
            "threshold_usd": "5000",
        })
        alert_id = create_resp.json()["id"]

        resp = await client.put(f"/v1/alerts/{alert_id}", json={
            "threshold_usd": "10000",
        })
        assert resp.status_code == 200
        assert float(resp.json()["threshold_usd"]) == 10000.0

    async def test_update_nonexistent_alert(self, client):
        resp = await client.put(
            "/v1/alerts/00000000-0000-0000-0000-000000000000",
            json={"threshold_usd": "5000"},
        )
        assert resp.status_code == 404

    async def test_delete_alert(self, client):
        create_resp = await client.post("/v1/alerts", json={
            "scope": "org",
            "period": "daily",
            "threshold_usd": "1000",
        })
        alert_id = create_resp.json()["id"]

        resp = await client.delete(f"/v1/alerts/{alert_id}")
        assert resp.status_code == 204

    async def test_delete_nonexistent_alert(self, client):
        resp = await client.delete("/v1/alerts/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_check_alerts_empty(self, client):
        resp = await client.get("/v1/alerts/check")
        assert resp.status_code == 200
        assert resp.json()["results"] == []
