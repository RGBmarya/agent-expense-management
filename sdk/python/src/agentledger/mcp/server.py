"""AgentLedger MCP server — card management tools for AI agents.

Run via: agentledger-mcp  (or python -m agentledger.mcp.server)
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from agentledger.mcp.client import AgentLedgerAPIClient
from agentledger.mcp import tools

server = Server("agentledger")
_client: AgentLedgerAPIClient | None = None


def _get_client() -> AgentLedgerAPIClient:
    global _client
    if _client is None:
        _client = AgentLedgerAPIClient()
    return _client


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[Tool] = [
    Tool(
        name="create_card",
        description="Create a new virtual card for making purchases. Returns card details including ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Human-readable label for the card"},
                "spending_limit_usd": {"type": "number", "description": "Total spending limit in USD"},
                "single_use": {"type": "boolean", "description": "Auto-close after first use", "default": False},
                "team": {"type": "string", "description": "Team attribution"},
                "project": {"type": "string", "description": "Project attribution"},
                "program_id": {"type": "string", "description": "Issue from a spend program template"},
            },
        },
    ),
    Tool(
        name="list_cards",
        description="List all virtual cards. Filter by status (active, frozen, closed).",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "frozen", "closed"]},
            },
        },
    ),
    Tool(
        name="get_card_details",
        description="Get encrypted card number (PAN), CVC, and expiry for making purchases.",
        inputSchema={
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "Card ID"},
            },
            "required": ["card_id"],
        },
    ),
    Tool(
        name="check_balance",
        description="Check remaining balance, daily and monthly spend on a card.",
        inputSchema={
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "Card ID"},
            },
            "required": ["card_id"],
        },
    ),
    Tool(
        name="freeze_card",
        description="Temporarily freeze a card. Can be unfrozen later.",
        inputSchema={
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "Card ID"},
            },
            "required": ["card_id"],
        },
    ),
    Tool(
        name="unfreeze_card",
        description="Unfreeze a previously frozen card.",
        inputSchema={
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "Card ID"},
            },
            "required": ["card_id"],
        },
    ),
    Tool(
        name="close_card",
        description="Permanently close a card. Cannot be undone.",
        inputSchema={
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "Card ID"},
            },
            "required": ["card_id"],
        },
    ),
    Tool(
        name="create_sub_card",
        description="Create a sub-card that inherits limits from a parent card.",
        inputSchema={
            "type": "object",
            "properties": {
                "parent_card_id": {"type": "string", "description": "Parent card ID"},
                "label": {"type": "string"},
                "spending_limit_usd": {"type": "number"},
            },
            "required": ["parent_card_id"],
        },
    ),
    Tool(
        name="get_transactions",
        description="Get transaction history for a card.",
        inputSchema={
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "Card ID"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["card_id"],
        },
    ),
    Tool(
        name="get_spend_summary",
        description="Get unified spend overview including both LLM API costs and card transactions.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="x402_fetch",
        description="Make an HTTP request and detect 402 Payment Required responses. Returns payment requirements if a 402 is received.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "method": {"type": "string", "default": "GET"},
            },
            "required": ["url"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOL_DEFINITIONS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    client = _get_client()

    handler_map = {
        "create_card": tools.create_card,
        "list_cards": tools.list_cards,
        "get_card_details": tools.get_card_details,
        "check_balance": tools.check_balance,
        "freeze_card": tools.freeze_card,
        "unfreeze_card": tools.unfreeze_card,
        "close_card": tools.close_card,
        "create_sub_card": tools.create_sub_card,
        "get_transactions": tools.get_transactions,
        "get_spend_summary": tools.get_spend_summary,
        "x402_fetch": tools.x402_fetch,
    }

    handler = handler_map.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(client, **arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def run_server() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    import asyncio
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
