"""Tests for shared query helpers."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest
from datetime import datetime, timezone

from app.queries import month_to_range, build_event_filters
from app.models import Event


class TestMonthToRange:
    def test_basic_month(self):
        start, end = month_to_range("2024-06")
        assert start == datetime(2024, 6, 1, tzinfo=timezone.utc)
        assert end == datetime(2024, 7, 1, tzinfo=timezone.utc)

    def test_december_rolls_to_next_year(self):
        start, end = month_to_range("2024-12")
        assert start == datetime(2024, 12, 1, tzinfo=timezone.utc)
        assert end == datetime(2025, 1, 1, tzinfo=timezone.utc)

    def test_january(self):
        start, end = month_to_range("2025-01")
        assert start == datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert end == datetime(2025, 2, 1, tzinfo=timezone.utc)

    def test_invalid_format_raises(self):
        with pytest.raises(Exception):
            month_to_range("invalid")


class TestBuildEventFilters:
    def test_org_only(self):
        filters = build_event_filters("org-123")
        assert len(filters) == 1

    def test_with_dates(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)
        filters = build_event_filters("org-123", start_date=start, end_date=end)
        assert len(filters) == 3

    def test_with_all_filters(self):
        filters = build_event_filters(
            "org-123",
            start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
            provider="openai",
            model="gpt-4",
            team="ml-team",
            project="chatbot",
            environment="production",
        )
        assert len(filters) == 8

    def test_none_values_excluded(self):
        filters = build_event_filters(
            "org-123",
            provider=None,
            model=None,
        )
        assert len(filters) == 1  # only org_id
