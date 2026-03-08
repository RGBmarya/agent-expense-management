"""Pydantic schemas for API request / response models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EventTypeEnum(str, Enum):
    llm_usage = "llm_usage"
    agent_transaction = "agent_transaction"


class RollupPeriodEnum(str, Enum):
    hourly = "hourly"
    daily = "daily"
    monthly = "monthly"


class TokenTypeEnum(str, Enum):
    input = "input"
    output = "output"
    cached_input = "cached_input"
    reasoning = "reasoning"


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class EventCreate(BaseModel):
    idempotency_key: str
    event_type: EventTypeEnum
    provider: str
    model: str
    timestamp: datetime
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    latency_ms: int | None = None
    amount_usd: Decimal | None = None
    merchant: str | None = None
    transaction_hash: str | None = None
    environment: str | None = None
    team: str | None = None
    project: str | None = None
    agent_id: str | None = None
    custom_tags: dict | None = None


class EventBatchRequest(BaseModel):
    events: list[EventCreate]


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    idempotency_key: str
    event_type: EventTypeEnum
    provider: str
    model: str
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    reasoning_tokens: int
    latency_ms: int | None
    amount_usd: Decimal | None
    estimated_cost_usd: Decimal | None
    environment: str | None
    team: str | None
    project: str | None
    agent_id: str | None
    custom_tags: dict | None


class EventBatchResponse(BaseModel):
    accepted: int
    duplicates: int
    events: list[EventResponse]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class BreakdownItem(BaseModel):
    key: str
    total_cost_usd: Decimal
    request_count: int


class OverviewResponse(BaseModel):
    mtd_spend_usd: Decimal
    previous_mtd_spend_usd: Decimal
    trend_30d: list[dict]
    top_providers: list[BreakdownItem]
    top_models: list[BreakdownItem]
    top_teams: list[BreakdownItem]


class ExploreRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    model: str
    team: str | None
    project: str | None
    environment: str | None
    total_cost_usd: Decimal
    request_count: int


class ExploreResponse(BaseModel):
    rows: list[ExploreRow]
    total: int


class SpendTimeseriesPoint(BaseModel):
    period_start: datetime
    total_cost_usd: Decimal
    request_count: int


class SpendOverTimeResponse(BaseModel):
    data: list[SpendTimeseriesPoint]
    granularity: str


# ---------------------------------------------------------------------------
# Budget Alerts
# ---------------------------------------------------------------------------

class BudgetAlertCreate(BaseModel):
    scope: str
    scope_value: str = ""
    period: RollupPeriodEnum
    threshold_usd: Decimal
    notify_channels: dict | None = None
    predictive: bool = False


class BudgetAlertUpdate(BaseModel):
    scope: str | None = None
    scope_value: str | None = None
    period: RollupPeriodEnum | None = None
    threshold_usd: Decimal | None = None
    notify_channels: dict | None = None
    predictive: bool | None = None


class BudgetAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    scope: str
    scope_value: str
    period: RollupPeriodEnum
    threshold_usd: Decimal
    notify_channels: dict | None
    predictive: bool
    last_triggered_at: datetime | None


class AlertCheckResult(BaseModel):
    alert_id: str
    scope: str
    scope_value: str
    threshold_usd: Decimal
    current_spend_usd: Decimal
    pct_used: float
    triggered: bool


class AlertCheckResponse(BaseModel):
    results: list[AlertCheckResult]


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

class MonthlyReportRow(BaseModel):
    month: str
    team: str
    project: str
    provider: str
    total_cost_usd: Decimal
    request_count: int


class MonthlyReportResponse(BaseModel):
    rows: list[MonthlyReportRow]
    grand_total_usd: Decimal


class InvoiceLineItem(BaseModel):
    provider: str
    invoice_amount_usd: Decimal


class InvoiceReconciliationRequest(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    line_items: list[InvoiceLineItem]


class ReconciliationRow(BaseModel):
    provider: str
    tracked_usd: Decimal
    invoice_usd: Decimal
    difference_usd: Decimal
    pct_difference: float


class InvoiceReconciliationResponse(BaseModel):
    month: str
    rows: list[ReconciliationRow]


# ---------------------------------------------------------------------------
# Auth / API Keys
# ---------------------------------------------------------------------------

class ApiKeyCreateRequest(BaseModel):
    label: str = ""


class ApiKeyCreateResponse(BaseModel):
    id: str
    raw_key: str
    label: str
    created_at: datetime


class ApiKeyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    created_at: datetime
    revoked_at: datetime | None


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyListItem]
