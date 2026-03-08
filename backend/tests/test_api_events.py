"""Integration tests for the events API."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest
from datetime import datetime, timezone


class TestIngestEvents:
    async def test_ingest_single_event(self, client):
        resp = await client.post("/v1/events", json={
            "events": [
                {
                    "idempotency_key": "test-1",
                    "event_type": "llm_usage",
                    "provider": "openai",
                    "model": "gpt-4",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "input_tokens": 100,
                    "output_tokens": 50,
                }
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] == 1
        assert data["duplicates"] == 0
        assert len(data["events"]) == 1
        assert data["events"][0]["provider"] == "openai"

    async def test_ingest_batch(self, client):
        events = [
            {
                "idempotency_key": f"batch-{i}",
                "event_type": "llm_usage",
                "provider": "openai",
                "model": "gpt-4",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_tokens": 100 * i,
                "output_tokens": 50 * i,
            }
            for i in range(5)
        ]
        resp = await client.post("/v1/events", json={"events": events})
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] == 5

    async def test_deduplication(self, client):
        event = {
            "idempotency_key": "dedup-test",
            "event_type": "llm_usage",
            "provider": "anthropic",
            "model": "claude-3",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_tokens": 200,
        }
        # First request
        resp1 = await client.post("/v1/events", json={"events": [event]})
        assert resp1.json()["accepted"] == 1

        # Second request with same key
        resp2 = await client.post("/v1/events", json={"events": [event]})
        assert resp2.json()["accepted"] == 0
        assert resp2.json()["duplicates"] == 1

    async def test_intra_batch_deduplication(self, client):
        event = {
            "idempotency_key": "intra-dedup",
            "event_type": "llm_usage",
            "provider": "openai",
            "model": "gpt-4",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        resp = await client.post("/v1/events", json={"events": [event, event]})
        data = resp.json()
        assert data["accepted"] == 1
        assert data["duplicates"] == 1

    async def test_empty_batch(self, client):
        resp = await client.post("/v1/events", json={"events": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["accepted"] == 0

    async def test_agent_transaction_type(self, client):
        resp = await client.post("/v1/events", json={
            "events": [
                {
                    "idempotency_key": "txn-1",
                    "event_type": "agent_transaction",
                    "provider": "stripe_issuing",
                    "model": "virtual_card",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "amount_usd": "25.50",
                    "merchant": "AWS",
                }
            ]
        })
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 1

    async def test_invalid_event_type(self, client):
        resp = await client.post("/v1/events", json={
            "events": [
                {
                    "idempotency_key": "bad-type",
                    "event_type": "invalid_type",
                    "provider": "openai",
                    "model": "gpt-4",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        })
        assert resp.status_code == 422

    async def test_missing_required_fields(self, client):
        resp = await client.post("/v1/events", json={
            "events": [
                {"idempotency_key": "missing-fields"}
            ]
        })
        assert resp.status_code == 422

    async def test_with_custom_tags(self, client):
        resp = await client.post("/v1/events", json={
            "events": [
                {
                    "idempotency_key": "tags-test",
                    "event_type": "llm_usage",
                    "provider": "openai",
                    "model": "gpt-4",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "custom_tags": {"env": "prod", "team": "ml"},
                }
            ]
        })
        assert resp.status_code == 200
        event = resp.json()["events"][0]
        assert event["custom_tags"] == {"env": "prod", "team": "ml"}

    async def test_unauthenticated_request(self, client):
        resp = await client.post(
            "/v1/events",
            json={"events": []},
            headers={"X-API-Key": "bad_key"},
        )
        assert resp.status_code == 401
