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


class CardStatus(str, enum.Enum):
    active = "active"
    frozen = "frozen"
    closed = "closed"
    pending = "pending"


class CardType(str, enum.Enum):
    single_use = "single_use"
    multi_use = "multi_use"


class TxnStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    declined = "declined"
    reversed = "reversed"


class PolicyScope(str, enum.Enum):
    org = "org"
    team = "team"
    card = "card"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    denied = "denied"


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
    virtual_cards: Mapped[list[VirtualCard]] = relationship(back_populates="organization")
    spend_policies: Mapped[list[SpendPolicy]] = relationship(back_populates="organization")
    spend_programs: Mapped[list[SpendProgram]] = relationship(back_populates="organization")


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


# ---------------------------------------------------------------------------
# Card / Policy / Program / Approval Models
# ---------------------------------------------------------------------------

class SpendPolicy(Base):
    __tablename__ = "spend_policies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    scope: Mapped[PolicyScope] = mapped_column(
        Enum(PolicyScope, name="policy_scope_enum", create_type=False),
        nullable=False, default=PolicyScope.card,
    )
    max_transaction_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    daily_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    monthly_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    allowed_mccs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    blocked_mccs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    blocked_merchants: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    allowed_merchants: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    require_approval_above_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    auto_close_after_first_use: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_expire_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="spend_policies")
    cards: Mapped[list[VirtualCard]] = relationship(
        secondary="card_policy_links", back_populates="policies"
    )


class SpendProgram(Base):
    __tablename__ = "spend_programs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    card_type: Mapped[CardType] = mapped_column(
        Enum(CardType, name="card_type_enum", create_type=False),
        default=CardType.multi_use,
    )
    spending_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    daily_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    monthly_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("spend_policies.id"), nullable=True
    )
    team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    project: Mapped[str | None] = mapped_column(String(128), nullable=True)
    auto_expire_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata_", JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="spend_programs")
    policy: Mapped[SpendPolicy | None] = relationship()
    cards: Mapped[list[VirtualCard]] = relationship(back_populates="spend_program")


class VirtualCard(Base):
    __tablename__ = "virtual_cards"
    __table_args__ = (
        Index("ix_virtual_cards_org_status", "org_id", "status"),
        Index("ix_virtual_cards_org_agent", "org_id", "agent_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    stripe_card_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )
    agent_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    parent_card_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("virtual_cards.id"), nullable=True
    )
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[CardStatus] = mapped_column(
        Enum(CardStatus, name="card_status_enum", create_type=False),
        nullable=False, default=CardStatus.active,
    )
    card_type: Mapped[CardType] = mapped_column(
        Enum(CardType, name="card_type_enum", create_type=False),
        nullable=False, default=CardType.multi_use,
    )
    # Card-level controls
    spending_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    daily_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    monthly_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    allowed_mccs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    blocked_mccs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Attribution
    team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    project: Mapped[str | None] = mapped_column(String(128), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata_", JSONB, nullable=True)
    # Stripe details (cached, non-sensitive)
    last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    exp_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exp_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stripe_cardholder_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Lifecycle
    spend_program_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("spend_programs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="virtual_cards")
    parent_card: Mapped[VirtualCard | None] = relationship(remote_side="VirtualCard.id")
    spend_program: Mapped[SpendProgram | None] = relationship(back_populates="cards")
    transactions: Mapped[list[CardTransaction]] = relationship(back_populates="card")
    policies: Mapped[list[SpendPolicy]] = relationship(
        secondary="card_policy_links", back_populates="cards"
    )


class CardTransaction(Base):
    __tablename__ = "card_transactions"
    __table_args__ = (
        Index("ix_card_transactions_card_created", "card_id", "created_at"),
        Index("ix_card_transactions_org_created", "org_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    card_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("virtual_cards.id"), nullable=False
    )
    event_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("events.id"), nullable=True
    )
    stripe_txn_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    merchant_mcc: Mapped[str | None] = mapped_column(String(8), nullable=True)
    merchant_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    merchant_country: Mapped[str | None] = mapped_column(String(4), nullable=True)
    status: Mapped[TxnStatus] = mapped_column(
        Enum(TxnStatus, name="txn_status_enum", create_type=False), nullable=False
    )
    decline_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    card: Mapped[VirtualCard] = relationship(back_populates="transactions")
    event: Mapped[Event | None] = relationship()


class CardPolicyLink(Base):
    __tablename__ = "card_policy_links"

    card_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("virtual_cards.id"), primary_key=True
    )
    policy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("spend_policies.id"), primary_key=True
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False
    )
    card_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("virtual_cards.id"), nullable=False
    )
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status_enum", create_type=False),
        nullable=False, default=ApprovalStatus.pending,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    card: Mapped[VirtualCard] = relationship()
    organization: Mapped[Organization] = relationship()
