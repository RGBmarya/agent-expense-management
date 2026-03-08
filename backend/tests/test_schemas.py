"""Tests for Pydantic schema validation."""

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import ValidationError

from app.schemas import (
    EventCreate,
    EventBatchRequest,
    BudgetAlertCreate,
    InvoiceReconciliationRequest,
)
from app.schemas_cards import (
    CardCreate,
    CardUpdate,
    SpendPolicyCreate,
    SpendProgramCreate,
    FundingRequest,
    ApprovalDecisionRequest,
)
from app.models import EventType, RollupPeriod, CardType, PolicyScope


class TestEventCreate:
    def test_valid_event(self):
        ev = EventCreate(
            idempotency_key="test-key-1",
            event_type=EventType.llm_usage,
            provider="openai",
            model="gpt-4",
            timestamp=datetime.now(timezone.utc),
            input_tokens=100,
            output_tokens=50,
        )
        assert ev.provider == "openai"

    def test_defaults(self):
        ev = EventCreate(
            idempotency_key="k",
            event_type=EventType.llm_usage,
            provider="openai",
            model="gpt-4",
            timestamp=datetime.now(timezone.utc),
        )
        assert ev.input_tokens == 0
        assert ev.output_tokens == 0
        assert ev.cached_tokens == 0
        assert ev.reasoning_tokens == 0
        assert ev.custom_tags is None

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            EventCreate(idempotency_key="k")

    def test_with_custom_tags(self):
        ev = EventCreate(
            idempotency_key="k",
            event_type=EventType.llm_usage,
            provider="openai",
            model="gpt-4",
            timestamp=datetime.now(timezone.utc),
            custom_tags={"env": "prod", "version": "1.0"},
        )
        assert ev.custom_tags["env"] == "prod"


class TestEventBatchRequest:
    def test_empty_batch(self):
        batch = EventBatchRequest(events=[])
        assert len(batch.events) == 0

    def test_single_event(self):
        batch = EventBatchRequest(events=[
            EventCreate(
                idempotency_key="k",
                event_type=EventType.llm_usage,
                provider="openai",
                model="gpt-4",
                timestamp=datetime.now(timezone.utc),
            )
        ])
        assert len(batch.events) == 1


class TestCardCreate:
    def test_minimal_card(self):
        card = CardCreate()
        assert card.card_type == CardType.multi_use
        assert card.label is None

    def test_with_limits(self):
        card = CardCreate(
            label="Test Card",
            spending_limit_usd=Decimal("1000"),
            daily_limit_usd=Decimal("100"),
            monthly_limit_usd=Decimal("500"),
        )
        assert card.spending_limit_usd == Decimal("1000")

    def test_negative_limits_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            CardCreate(spending_limit_usd=Decimal("-100"))

    def test_zero_limit_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            CardCreate(spending_limit_usd=Decimal("0"))


class TestSpendPolicyCreate:
    def test_minimal_policy(self):
        policy = SpendPolicyCreate(name="Default Policy")
        assert policy.scope == PolicyScope.card
        assert policy.is_default is False

    def test_full_policy(self):
        policy = SpendPolicyCreate(
            name="Strict Policy",
            scope=PolicyScope.org,
            max_transaction_usd=Decimal("500"),
            daily_limit_usd=Decimal("1000"),
            monthly_limit_usd=Decimal("5000"),
            allowed_mccs=["5411", "5812"],
            blocked_merchants=["Casino"],
            require_approval_above_usd=Decimal("100"),
            auto_close_after_first_use=True,
            auto_expire_days=30,
        )
        assert policy.max_transaction_usd == Decimal("500")


class TestFundingRequest:
    def test_positive_amount(self):
        req = FundingRequest(amount_usd=Decimal("100"))
        assert req.amount_usd == Decimal("100")

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError):
            FundingRequest(amount_usd=Decimal("0"))

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            FundingRequest(amount_usd=Decimal("-50"))


class TestInvoiceReconciliationRequest:
    def test_valid_month_format(self):
        req = InvoiceReconciliationRequest(
            month="2024-06",
            line_items=[],
        )
        assert req.month == "2024-06"

    def test_invalid_month_format(self):
        with pytest.raises(ValidationError):
            InvoiceReconciliationRequest(
                month="June 2024",
                line_items=[],
            )


class TestBudgetAlertCreate:
    def test_valid_alert(self):
        alert = BudgetAlertCreate(
            scope="org",
            period=RollupPeriod.monthly,
            threshold_usd=Decimal("10000"),
        )
        assert alert.predictive is False

    def test_with_notify_channels(self):
        alert = BudgetAlertCreate(
            scope="team",
            scope_value="ml-team",
            period=RollupPeriod.daily,
            threshold_usd=Decimal("500"),
            notify_channels={"slack": "#alerts"},
        )
        assert alert.notify_channels["slack"] == "#alerts"
