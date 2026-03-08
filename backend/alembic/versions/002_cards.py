"""Add virtual cards, policies, spend programs, and approvals.

Revision ID: 002_cards
Revises: 001_initial
Create Date: 2026-03-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "002_cards"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Enums -----------------------------------------------------------------
    card_status_enum = sa.Enum(
        "active", "frozen", "closed", "pending",
        name="card_status_enum",
    )
    card_type_enum = sa.Enum(
        "single_use", "multi_use",
        name="card_type_enum",
    )
    txn_status_enum = sa.Enum(
        "pending", "completed", "declined", "reversed",
        name="txn_status_enum",
    )
    policy_scope_enum = sa.Enum(
        "org", "team", "card",
        name="policy_scope_enum",
    )
    approval_status_enum = sa.Enum(
        "pending", "approved", "denied",
        name="approval_status_enum",
    )

    card_status_enum.create(op.get_bind(), checkfirst=True)
    card_type_enum.create(op.get_bind(), checkfirst=True)
    txn_status_enum.create(op.get_bind(), checkfirst=True)
    policy_scope_enum.create(op.get_bind(), checkfirst=True)
    approval_status_enum.create(op.get_bind(), checkfirst=True)

    # -- spend_policies --------------------------------------------------------
    op.create_table(
        "spend_policies",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("scope", policy_scope_enum, nullable=False, server_default="card"),
        sa.Column("max_transaction_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("daily_limit_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("monthly_limit_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("allowed_mccs", postgresql.JSONB, nullable=True),
        sa.Column("blocked_mccs", postgresql.JSONB, nullable=True),
        sa.Column("blocked_merchants", postgresql.JSONB, nullable=True),
        sa.Column("allowed_merchants", postgresql.JSONB, nullable=True),
        sa.Column("require_approval_above_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("auto_close_after_first_use", sa.Boolean, server_default="false"),
        sa.Column("auto_expire_days", sa.Integer, nullable=True),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_spend_policies_org", "spend_policies", ["org_id"])

    # -- spend_programs --------------------------------------------------------
    op.create_table(
        "spend_programs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("card_type", card_type_enum, server_default="multi_use"),
        sa.Column("spending_limit_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("daily_limit_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("monthly_limit_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "policy_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("spend_policies.id"),
            nullable=True,
        ),
        sa.Column("team", sa.String(128), nullable=True),
        sa.Column("project", sa.String(128), nullable=True),
        sa.Column("auto_expire_days", sa.Integer, nullable=True),
        sa.Column("metadata_", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # -- virtual_cards ---------------------------------------------------------
    op.create_table(
        "virtual_cards",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("stripe_card_id", sa.String(128), unique=True, nullable=True),
        sa.Column("agent_id", sa.String(256), nullable=True),
        sa.Column(
            "parent_card_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("virtual_cards.id"),
            nullable=True,
        ),
        sa.Column("label", sa.String(256), nullable=True),
        sa.Column("status", card_status_enum, nullable=False, server_default="active"),
        sa.Column("card_type", card_type_enum, nullable=False, server_default="multi_use"),
        # Card-level controls
        sa.Column("spending_limit_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("daily_limit_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("monthly_limit_usd", sa.Numeric(14, 2), nullable=True),
        sa.Column("allowed_mccs", postgresql.JSONB, nullable=True),
        sa.Column("blocked_mccs", postgresql.JSONB, nullable=True),
        # Attribution
        sa.Column("team", sa.String(128), nullable=True),
        sa.Column("project", sa.String(128), nullable=True),
        sa.Column("environment", sa.String(64), nullable=True),
        sa.Column("metadata_", postgresql.JSONB, nullable=True),
        # Stripe details (cached, non-sensitive)
        sa.Column("last4", sa.String(4), nullable=True),
        sa.Column("exp_month", sa.Integer, nullable=True),
        sa.Column("exp_year", sa.Integer, nullable=True),
        sa.Column("stripe_cardholder_id", sa.String(128), nullable=True),
        # Lifecycle
        sa.Column(
            "spend_program_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("spend_programs.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_virtual_cards_org_status", "virtual_cards", ["org_id", "status"])
    op.create_index("ix_virtual_cards_org_agent", "virtual_cards", ["org_id", "agent_id"])

    # -- card_transactions -----------------------------------------------------
    op.create_table(
        "card_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "card_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("virtual_cards.id"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("events.id"),
            nullable=True,
        ),
        sa.Column("stripe_txn_id", sa.String(128), unique=True, nullable=True),
        sa.Column("amount_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("merchant_name", sa.String(256), nullable=True),
        sa.Column("merchant_mcc", sa.String(8), nullable=True),
        sa.Column("merchant_city", sa.String(128), nullable=True),
        sa.Column("merchant_country", sa.String(4), nullable=True),
        sa.Column("status", txn_status_enum, nullable=False),
        sa.Column("decline_reason", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_card_transactions_card_created",
        "card_transactions",
        ["card_id", "created_at"],
    )
    op.create_index(
        "ix_card_transactions_org_created",
        "card_transactions",
        ["org_id", "created_at"],
    )

    # -- card_policy_links -----------------------------------------------------
    op.create_table(
        "card_policy_links",
        sa.Column(
            "card_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("virtual_cards.id"),
            primary_key=True,
        ),
        sa.Column(
            "policy_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("spend_policies.id"),
            primary_key=True,
        ),
    )

    # -- approval_requests -----------------------------------------------------
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "card_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("virtual_cards.id"),
            nullable=False,
        ),
        sa.Column("amount_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("merchant_name", sa.String(256), nullable=True),
        sa.Column("status", approval_status_enum, nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.String(256), nullable=True),
        sa.Column("reason", sa.String(512), nullable=True),
    )
    op.create_index(
        "ix_approval_requests_org_status",
        "approval_requests",
        ["org_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("approval_requests")
    op.drop_table("card_policy_links")
    op.drop_table("card_transactions")
    op.drop_table("virtual_cards")
    op.drop_table("spend_programs")
    op.drop_table("spend_policies")

    op.execute("DROP TYPE IF EXISTS approval_status_enum")
    op.execute("DROP TYPE IF EXISTS policy_scope_enum")
    op.execute("DROP TYPE IF EXISTS txn_status_enum")
    op.execute("DROP TYPE IF EXISTS card_type_enum")
    op.execute("DROP TYPE IF EXISTS card_status_enum")
