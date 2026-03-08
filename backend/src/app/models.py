"""SQLAlchemy ORM models for AgentLedger."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all models."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EventType(str, enum.Enum):
    llm_usage = "llm_usage"
    agent_transaction = "agent_transaction"


class RollupPeriod(str, enum.Enum):
    hourly = "hourly"
    daily = "daily"
    monthly = "monthly"


class TokenType(str, enum.Enum):
    input = "input"
    output = "output"
    cached_input = "cached_input"
    reasoning = "reasoning"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="organization")
    events: Mapped[list[Event]] = relationship(back_populates="organization")
    budget_alerts: Mapped[list[BudgetAlert]] = relationship(back_populates="organization")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization: Mapped[Organization] = relationship(back_populates="api_keys")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("org_id", "idempotency_key", name="uq_event_idempotency"),
        Index("ix_events_org_timestamp", "org_id", "timestamp"),
        Index("ix_events_org_provider_model", "org_id", "provider", "model"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type_enum"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), nullable=True
    )
    merchant: Mapped[str | None] = mapped_column(String(256), nullable=True)
    transaction_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(64), nullable=True)
    team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    project: Mapped[str | None] = mapped_column(String(128), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    custom_tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6), nullable=True
    )

    organization: Mapped[Organization] = relationship(back_populates="events")


class CostRollup(Base):
    __tablename__ = "cost_rollups"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "period", "period_start", "event_type",
            "provider", "model", "team", "project", "environment",
            name="uq_cost_rollup",
        ),
        Index("ix_cost_rollups_lookup", "org_id", "period", "period_start"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    period: Mapped[RollupPeriod] = mapped_column(
        Enum(RollupPeriod, name="rollup_period_enum"), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    team: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    project: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    environment: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), nullable=False, default=0
    )
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class BudgetAlert(Base):
    __tablename__ = "budget_alerts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_value: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    period: Mapped[RollupPeriod] = mapped_column(
        Enum(RollupPeriod, name="rollup_period_enum", create_type=False), nullable=False
    )
    threshold_usd: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notify_channels: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    predictive: Mapped[bool] = mapped_column(Boolean, default=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization: Mapped[Organization] = relationship(back_populates="budget_alerts")


class PricingTable(Base):
    __tablename__ = "pricing_table"
    __table_args__ = (
        Index(
            "ix_pricing_lookup",
            "provider", "model", "token_type", "effective_from",
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    token_type: Mapped[TokenType] = mapped_column(
        Enum(TokenType, name="token_type_enum"), nullable=False
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cost_per_million_tokens: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False
    )
