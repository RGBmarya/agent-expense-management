"""Pydantic schemas for card, policy, program, and approval endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ApprovalStatus, CardStatus, CardType, PolicyScope


# ---------------------------------------------------------------------------
# Virtual Cards
# ---------------------------------------------------------------------------

class CardCreate(BaseModel):
    label: str | None = Field(None, max_length=256)
    agent_id: str | None = Field(None, max_length=256)
    card_type: CardType = CardType.multi_use
    spending_limit_usd: Decimal | None = Field(None, gt=0)
    daily_limit_usd: Decimal | None = Field(None, gt=0)
    monthly_limit_usd: Decimal | None = Field(None, gt=0)
    allowed_mccs: list[str] | None = None
    blocked_mccs: list[str] | None = None
    team: str | None = Field(None, max_length=128)
    project: str | None = Field(None, max_length=128)
    environment: str | None = Field(None, max_length=64)
    metadata: dict | None = Field(None, alias="metadata")
    # Optional: create from a spend program
    spend_program_id: str | None = None
    # Optional: create as sub-card of a parent
    parent_card_id: str | None = None


class CardUpdate(BaseModel):
    label: str | None = None
    spending_limit_usd: Decimal | None = None
    daily_limit_usd: Decimal | None = None
    monthly_limit_usd: Decimal | None = None
    allowed_mccs: list[str] | None = None
    blocked_mccs: list[str] | None = None
    team: str | None = None
    project: str | None = None


class CardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    stripe_card_id: str | None
    agent_id: str | None
    parent_card_id: str | None
    label: str | None
    status: CardStatus
    card_type: CardType
    spending_limit_usd: Decimal | None
    daily_limit_usd: Decimal | None
    monthly_limit_usd: Decimal | None
    allowed_mccs: list[str] | None
    blocked_mccs: list[str] | None
    team: str | None
    project: str | None
    environment: str | None
    last4: str | None
    exp_month: int | None
    exp_year: int | None
    spend_program_id: str | None
    created_at: datetime
    closed_at: datetime | None
    expires_at: datetime | None


class CardBalanceResponse(BaseModel):
    card_id: str
    spending_limit_usd: Decimal | None
    total_spent_usd: Decimal
    remaining_usd: Decimal | None
    daily_spent_usd: Decimal
    daily_limit_usd: Decimal | None
    monthly_spent_usd: Decimal
    monthly_limit_usd: Decimal | None


class CardSensitiveResponse(BaseModel):
    card_id: str
    number: str  # encrypted PAN
    cvc: str  # encrypted CVC
    exp_month: int
    exp_year: int


# ---------------------------------------------------------------------------
# Card Transactions
# ---------------------------------------------------------------------------

class CardTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    card_id: str
    event_id: str | None
    stripe_txn_id: str | None
    amount_usd: Decimal
    merchant_name: str | None
    merchant_mcc: str | None
    merchant_city: str | None
    merchant_country: str | None
    status: str
    decline_reason: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Spend Policies
# ---------------------------------------------------------------------------

class SpendPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    scope: PolicyScope = PolicyScope.card
    max_transaction_usd: Decimal | None = Field(None, gt=0)
    daily_limit_usd: Decimal | None = Field(None, gt=0)
    monthly_limit_usd: Decimal | None = Field(None, gt=0)
    allowed_mccs: list[str] | None = None
    blocked_mccs: list[str] | None = None
    blocked_merchants: list[str] | None = None
    allowed_merchants: list[str] | None = None
    require_approval_above_usd: Decimal | None = None
    auto_close_after_first_use: bool = False
    auto_expire_days: int | None = None
    is_default: bool = False


class SpendPolicyUpdate(BaseModel):
    name: str | None = None
    scope: PolicyScope | None = None
    max_transaction_usd: Decimal | None = None
    daily_limit_usd: Decimal | None = None
    monthly_limit_usd: Decimal | None = None
    allowed_mccs: list[str] | None = None
    blocked_mccs: list[str] | None = None
    blocked_merchants: list[str] | None = None
    allowed_merchants: list[str] | None = None
    require_approval_above_usd: Decimal | None = None
    auto_close_after_first_use: bool | None = None
    auto_expire_days: int | None = None
    is_default: bool | None = None


class SpendPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    name: str
    scope: PolicyScope
    max_transaction_usd: Decimal | None
    daily_limit_usd: Decimal | None
    monthly_limit_usd: Decimal | None
    allowed_mccs: list[str] | None
    blocked_mccs: list[str] | None
    blocked_merchants: list[str] | None
    allowed_merchants: list[str] | None
    require_approval_above_usd: Decimal | None
    auto_close_after_first_use: bool
    auto_expire_days: int | None
    is_default: bool
    created_at: datetime


class PolicyAttachRequest(BaseModel):
    card_ids: list[str]


# ---------------------------------------------------------------------------
# Spend Programs
# ---------------------------------------------------------------------------

class SpendProgramCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    card_type: CardType = CardType.multi_use
    spending_limit_usd: Decimal | None = Field(None, gt=0)
    daily_limit_usd: Decimal | None = Field(None, gt=0)
    monthly_limit_usd: Decimal | None = Field(None, gt=0)
    policy_id: str | None = None
    team: str | None = None
    project: str | None = None
    auto_expire_days: int | None = None
    metadata: dict | None = None


class SpendProgramUpdate(BaseModel):
    name: str | None = None
    card_type: CardType | None = None
    spending_limit_usd: Decimal | None = None
    daily_limit_usd: Decimal | None = None
    monthly_limit_usd: Decimal | None = None
    policy_id: str | None = None
    team: str | None = None
    project: str | None = None
    auto_expire_days: int | None = None
    is_active: bool | None = None


class SpendProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    name: str
    card_type: CardType
    spending_limit_usd: Decimal | None
    daily_limit_usd: Decimal | None
    monthly_limit_usd: Decimal | None
    policy_id: str | None
    team: str | None
    project: str | None
    auto_expire_days: int | None
    is_active: bool
    created_at: datetime


class ProgramIssueRequest(BaseModel):
    agent_id: str | None = None
    label: str | None = None
    environment: str | None = None


# ---------------------------------------------------------------------------
# Approval Requests
# ---------------------------------------------------------------------------

class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    card_id: str
    amount_usd: Decimal
    merchant_name: str | None
    status: ApprovalStatus
    requested_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    reason: str | None


class ApprovalDecisionRequest(BaseModel):
    reason: str | None = None


# ---------------------------------------------------------------------------
# Funding
# ---------------------------------------------------------------------------

class FundingRequest(BaseModel):
    amount_usd: Decimal = Field(..., gt=0)


class FundingResponse(BaseModel):
    checkout_url: str
