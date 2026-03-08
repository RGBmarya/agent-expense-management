"""Seed script to populate the pricing_table with current (March 2026) pricing data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session_factory
from app.models import PricingTable, TokenType

# Effective-from date for all seed rows
EFFECTIVE_FROM = datetime(2025, 1, 1, tzinfo=timezone.utc)

# Pricing data: (provider, model, input, output, cached_input, reasoning)
# Values are cost per 1 million tokens in USD.
PRICING: list[dict] = [
    # ── OpenAI ───────────────────────────────────────────────────────────
    {
        "provider": "openai",
        "model": "gpt-4o",
        "input": Decimal("2.50"),
        "output": Decimal("10.00"),
        "cached_input": Decimal("1.25"),
        "reasoning": Decimal("10.00"),
    },
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "input": Decimal("0.15"),
        "output": Decimal("0.60"),
        "cached_input": Decimal("0.075"),
        "reasoning": Decimal("0.60"),
    },
    {
        "provider": "openai",
        "model": "gpt-4-turbo",
        "input": Decimal("10.00"),
        "output": Decimal("30.00"),
        "cached_input": Decimal("5.00"),
        "reasoning": Decimal("30.00"),
    },
    {
        "provider": "openai",
        "model": "o1",
        "input": Decimal("15.00"),
        "output": Decimal("60.00"),
        "cached_input": Decimal("7.50"),
        "reasoning": Decimal("60.00"),
    },
    {
        "provider": "openai",
        "model": "o1-mini",
        "input": Decimal("3.00"),
        "output": Decimal("12.00"),
        "cached_input": Decimal("1.50"),
        "reasoning": Decimal("12.00"),
    },
    {
        "provider": "openai",
        "model": "o3-mini",
        "input": Decimal("1.10"),
        "output": Decimal("4.40"),
        "cached_input": Decimal("0.55"),
        "reasoning": Decimal("4.40"),
    },
    # ── Anthropic ────────────────────────────────────────────────────────
    {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "input": Decimal("3.00"),
        "output": Decimal("15.00"),
        "cached_input": Decimal("0.30"),
        "reasoning": Decimal("15.00"),
    },
    {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "input": Decimal("0.80"),
        "output": Decimal("4.00"),
        "cached_input": Decimal("0.08"),
        "reasoning": Decimal("4.00"),
    },
    {
        "provider": "anthropic",
        "model": "claude-opus-4-20250115",
        "input": Decimal("15.00"),
        "output": Decimal("75.00"),
        "cached_input": Decimal("1.50"),
        "reasoning": Decimal("75.00"),
    },
]

TOKEN_TYPES = [
    ("input", TokenType.input),
    ("output", TokenType.output),
    ("cached_input", TokenType.cached_input),
    ("reasoning", TokenType.reasoning),
]


async def seed_pricing() -> int:
    """Insert pricing rows if they don't already exist. Returns count of rows created."""
    rows_to_insert = []
    for entry in PRICING:
        for key, ttype in TOKEN_TYPES:
            cost = entry.get(key)
            if cost is None:
                continue
            rows_to_insert.append({
                "id": str(uuid4()),
                "provider": entry["provider"],
                "model": entry["model"],
                "token_type": ttype,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
                "cost_per_million_tokens": cost,
            })

    if not rows_to_insert:
        return 0

    async with async_session_factory() as session:
        stmt = pg_insert(PricingTable).values(rows_to_insert).on_conflict_do_nothing(
            index_elements=["provider", "model", "token_type", "effective_from"],
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount  # type: ignore[return-value]


if __name__ == "__main__":
    count = asyncio.run(seed_pricing())
    print(f"Seeded {count} pricing rows.")
