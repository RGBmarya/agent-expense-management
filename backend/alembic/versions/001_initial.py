"""Initial migration – create all tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Enums -----------------------------------------------------------------
    event_type_enum = sa.Enum("llm_usage", "agent_transaction", name="event_type_enum")
    rollup_period_enum = sa.Enum("hourly", "daily", "monthly", name="rollup_period_enum")
    token_type_enum = sa.Enum("input", "output", "cached_input", "reasoning", name="token_type_enum")

    event_type_enum.create(op.get_bind(), checkfirst=True)
    rollup_period_enum.create(op.get_bind(), checkfirst=True)
    token_type_enum.create(op.get_bind(), checkfirst=True)

    # -- organizations ---------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- api_keys --------------------------------------------------------------
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("key_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("label", sa.String(256), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -- events ----------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(256), nullable=False),
        sa.Column("event_type", event_type_enum, nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_tokens", sa.Integer, server_default="0"),
        sa.Column("output_tokens", sa.Integer, server_default="0"),
        sa.Column("cached_tokens", sa.Integer, server_default="0"),
        sa.Column("reasoning_tokens", sa.Integer, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("amount_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("merchant", sa.String(256), nullable=True),
        sa.Column("transaction_hash", sa.String(256), nullable=True),
        sa.Column("environment", sa.String(64), nullable=True),
        sa.Column("team", sa.String(128), nullable=True),
        sa.Column("project", sa.String(128), nullable=True),
        sa.Column("agent_id", sa.String(256), nullable=True),
        sa.Column("custom_tags", postgresql.JSONB, nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.UniqueConstraint("org_id", "idempotency_key", name="uq_event_idempotency"),
    )
    op.create_index("ix_events_org_timestamp", "events", ["org_id", "timestamp"])
    op.create_index("ix_events_org_provider_model", "events", ["org_id", "provider", "model"])

    # -- cost_rollups ----------------------------------------------------------
    op.create_table(
        "cost_rollups",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("period", rollup_period_enum, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False, server_default=""),
        sa.Column("provider", sa.String(64), nullable=False, server_default=""),
        sa.Column("model", sa.String(128), nullable=False, server_default=""),
        sa.Column("team", sa.String(128), nullable=False, server_default=""),
        sa.Column("project", sa.String(128), nullable=False, server_default=""),
        sa.Column("environment", sa.String(64), nullable=False, server_default=""),
        sa.Column("total_cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("request_count", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "org_id", "period", "period_start", "event_type",
            "provider", "model", "team", "project", "environment",
            name="uq_cost_rollup",
        ),
    )
    op.create_index("ix_cost_rollups_lookup", "cost_rollups", ["org_id", "period", "period_start"])

    # -- budget_alerts ---------------------------------------------------------
    op.create_table(
        "budget_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("scope_value", sa.String(256), nullable=False, server_default=""),
        sa.Column("period", rollup_period_enum, nullable=False),
        sa.Column("threshold_usd", sa.Numeric(14, 2), nullable=False),
        sa.Column("notify_channels", postgresql.JSONB, nullable=True),
        sa.Column("predictive", sa.Boolean, server_default="false"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -- pricing_table ---------------------------------------------------------
    op.create_table(
        "pricing_table",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("token_type", token_type_enum, nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_per_million_tokens", sa.Numeric(12, 4), nullable=False),
    )
    op.create_index(
        "ix_pricing_lookup",
        "pricing_table",
        ["provider", "model", "token_type", "effective_from"],
    )


def downgrade() -> None:
    op.drop_table("pricing_table")
    op.drop_table("budget_alerts")
    op.drop_table("cost_rollups")
    op.drop_table("events")
    op.drop_table("api_keys")
    op.drop_table("organizations")

    op.execute("DROP TYPE IF EXISTS token_type_enum")
    op.execute("DROP TYPE IF EXISTS rollup_period_enum")
    op.execute("DROP TYPE IF EXISTS event_type_enum")
