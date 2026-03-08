"""MCP tool definitions for AgentLedger card management."""

from __future__ import annotations

from typing import Any, Optional

from agentledger.mcp.client import AgentLedgerAPIClient


async def create_card(
    client: AgentLedgerAPIClient,
    label: Optional[str] = None,
    spending_limit_usd: Optional[float] = None,
    single_use: bool = False,
    team: Optional[str] = None,
    project: Optional[str] = None,
    program_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create a new virtual card for making purchases."""
    body: dict[str, Any] = {}
    if label:
        body["label"] = label
    if spending_limit_usd is not None:
        body["spending_limit_usd"] = spending_limit_usd
    if single_use:
        body["card_type"] = "single_use"
    if team:
        body["team"] = team
    if project:
        body["project"] = project
    if program_id:
        body["spend_program_id"] = program_id
    return await client.create_card(**body)


async def list_cards(
    client: AgentLedgerAPIClient,
    status: Optional[str] = None,
) -> list[dict[str, Any]]:
    """List all virtual cards with optional status filter."""
    params: dict[str, str] = {}
    if status:
        params["status"] = status
    return await client.list_cards(**params)


async def get_card_details(
    client: AgentLedgerAPIClient,
    card_id: str,
) -> dict[str, Any]:
    """Get encrypted PAN + CVC + expiry for making purchases."""
    return await client.get_card_sensitive(card_id)


async def check_balance(
    client: AgentLedgerAPIClient,
    card_id: str,
) -> dict[str, Any]:
    """Check remaining balance on a card."""
    return await client.get_card_balance(card_id)


async def freeze_card(
    client: AgentLedgerAPIClient,
    card_id: str,
) -> dict[str, Any]:
    """Temporarily freeze a card."""
    return await client.freeze_card(card_id)


async def unfreeze_card(
    client: AgentLedgerAPIClient,
    card_id: str,
) -> dict[str, Any]:
    """Unfreeze a frozen card."""
    return await client.unfreeze_card(card_id)


async def close_card(
    client: AgentLedgerAPIClient,
    card_id: str,
) -> dict[str, Any]:
    """Permanently close a card."""
    return await client.close_card(card_id)


async def create_sub_card(
    client: AgentLedgerAPIClient,
    parent_card_id: str,
    label: Optional[str] = None,
    spending_limit_usd: Optional[float] = None,
) -> dict[str, Any]:
    """Create a sub-card with inherited limits from parent."""
    body: dict[str, Any] = {}
    if label:
        body["label"] = label
    if spending_limit_usd is not None:
        body["spending_limit_usd"] = spending_limit_usd
    return await client.create_sub_card(parent_card_id, **body)


async def get_transactions(
    client: AgentLedgerAPIClient,
    card_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get transaction history for a card."""
    return await client.get_card_transactions(card_id, limit=limit)


async def get_spend_summary(
    client: AgentLedgerAPIClient,
) -> dict[str, Any]:
    """Get unified spend overview (LLM + card)."""
    return await client.get_overview()


async def x402_fetch(
    client: AgentLedgerAPIClient,
    url: str,
    method: str = "GET",
) -> dict[str, Any]:
    """Make an HTTP request that detects 402 Payment Required responses.

    Returns payment requirements if 402 is received.
    """
    return await client.x402_fetch(url, method=method)
