"""Tests for cost computation engine."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.cost_engine import _PricingCache, compute_event_cost
from app.models import PricingTable, TokenType


class TestPricingCache:
    def test_lookup_empty_cache(self):
        cache = _PricingCache()
        result = cache.lookup("openai", "gpt-4", "input", datetime.now(timezone.utc))
        assert result is None

    def test_lookup_with_data(self):
        cache = _PricingCache()
        cache._store = {
            ("openai", "gpt-4", "input"): [
                {
                    "effective_from": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "effective_to": None,
                    "cost_per_million_tokens": Decimal("30.00"),
                }
            ]
        }
        result = cache.lookup(
            "openai", "gpt-4", "input",
            datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        assert result == Decimal("30.00")

    def test_lookup_respects_effective_dates(self):
        cache = _PricingCache()
        cache._store = {
            ("openai", "gpt-4", "input"): [
                {
                    "effective_from": datetime(2024, 6, 1, tzinfo=timezone.utc),
                    "effective_to": None,
                    "cost_per_million_tokens": Decimal("15.00"),
                },
                {
                    "effective_from": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "effective_to": datetime(2024, 6, 1, tzinfo=timezone.utc),
                    "cost_per_million_tokens": Decimal("30.00"),
                },
            ]
        }
        # Before price change
        old = cache.lookup(
            "openai", "gpt-4", "input",
            datetime(2024, 3, 1, tzinfo=timezone.utc),
        )
        assert old == Decimal("30.00")

        # After price change
        new = cache.lookup(
            "openai", "gpt-4", "input",
            datetime(2024, 7, 1, tzinfo=timezone.utc),
        )
        assert new == Decimal("15.00")

    def test_lookup_no_match_for_timestamp(self):
        cache = _PricingCache()
        cache._store = {
            ("openai", "gpt-4", "input"): [
                {
                    "effective_from": datetime(2025, 1, 1, tzinfo=timezone.utc),
                    "effective_to": None,
                    "cost_per_million_tokens": Decimal("30.00"),
                }
            ]
        }
        result = cache.lookup(
            "openai", "gpt-4", "input",
            datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        assert result is None

    def test_stale_check(self):
        cache = _PricingCache(ttl_seconds=0)
        assert cache._is_stale() is True


class TestComputeEventCost:
    async def test_zero_tokens(self, session):
        cost = await compute_event_cost(
            session,
            provider="openai",
            model="gpt-4",
            timestamp=datetime.now(timezone.utc),
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == Decimal(0)

    async def test_with_pricing_data(self, session):
        """Cost computation with seeded pricing data."""
        from app.cost_engine import pricing_cache

        # Seed the cache directly
        pricing_cache._store = {
            ("openai", "gpt-4", "input"): [
                {
                    "effective_from": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "effective_to": None,
                    "cost_per_million_tokens": Decimal("30.00"),
                }
            ],
            ("openai", "gpt-4", "output"): [
                {
                    "effective_from": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "effective_to": None,
                    "cost_per_million_tokens": Decimal("60.00"),
                }
            ],
        }
        pricing_cache._last_refresh = float("inf")  # prevent refresh

        cost = await compute_event_cost(
            session,
            provider="openai",
            model="gpt-4",
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            input_tokens=1000,
            output_tokens=500,
        )
        # (1000/1M)*30 + (500/1M)*60 = 0.03 + 0.03 = 0.06
        assert cost == Decimal("0.060000")

    async def test_unknown_model_returns_zero(self, session):
        from app.cost_engine import pricing_cache
        pricing_cache._store = {}
        pricing_cache._last_refresh = float("inf")

        cost = await compute_event_cost(
            session,
            provider="unknown",
            model="unknown",
            timestamp=datetime.now(timezone.utc),
            input_tokens=1000,
        )
        assert cost == Decimal(0)
