"""Cost computation engine with in-memory pricing cache."""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import PricingTable, TokenType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class _PricingCache:
    """Simple in-memory cache for pricing lookups keyed by (provider, model, token_type)."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._store: dict[tuple[str, str, str], list[dict]] = {}
        self._last_refresh: float = 0.0
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()

    async def refresh(self, session: AsyncSession) -> None:
        """Reload all pricing rows from the database."""
        result = await session.execute(
            select(PricingTable).order_by(
                PricingTable.provider,
                PricingTable.model,
                PricingTable.token_type,
                PricingTable.effective_from.desc(),
            )
        )
        rows = result.scalars().all()

        store: dict[tuple[str, str, str], list[dict]] = {}
        for row in rows:
            key = (row.provider, row.model, row.token_type.value)
            entry = {
                "effective_from": row.effective_from,
                "effective_to": row.effective_to,
                "cost_per_million_tokens": row.cost_per_million_tokens,
            }
            store.setdefault(key, []).append(entry)

        self._store = store
        self._last_refresh = asyncio.get_event_loop().time()

    def _is_stale(self) -> bool:
        try:
            now = asyncio.get_event_loop().time()
        except RuntimeError:
            return True
        return (now - self._last_refresh) > self._ttl

    async def ensure_fresh(self, session: AsyncSession) -> None:
        if self._is_stale():
            async with self._lock:
                # Double-check after acquiring lock
                if self._is_stale():
                    await self.refresh(session)

    def lookup(
        self, provider: str, model: str, token_type: str, timestamp: datetime
    ) -> Decimal | None:
        """Return cost-per-million-tokens for the given parameters at a point in time."""
        entries = self._store.get((provider, model, token_type), [])
        for entry in entries:
            eff_from: datetime = entry["effective_from"]
            eff_to: datetime | None = entry["effective_to"]
            ts = timestamp if timestamp.tzinfo else timestamp.replace(
                tzinfo=eff_from.tzinfo
            )
            if ts >= eff_from and (eff_to is None or ts < eff_to):
                return entry["cost_per_million_tokens"]
        return None


# Module-level singleton
pricing_cache = _PricingCache()


async def lookup_price(
    session: AsyncSession,
    provider: str,
    model: str,
    token_type: str,
    timestamp: datetime,
) -> Decimal:
    """Look up the price per million tokens, returning Decimal(0) if not found."""
    await pricing_cache.ensure_fresh(session)
    price = pricing_cache.lookup(provider, model, token_type, timestamp)
    return price if price is not None else Decimal(0)


async def compute_event_cost(
    session: AsyncSession,
    *,
    provider: str,
    model: str,
    timestamp: datetime,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> Decimal:
    """Compute the estimated cost in USD for a single event.

    Handles four token categories:
      - input tokens   -> TokenType.input
      - output tokens  -> TokenType.output
      - cached tokens  -> TokenType.cached_input
      - reasoning tokens -> TokenType.reasoning
    """
    await pricing_cache.ensure_fresh(session)

    million = Decimal("1000000")
    total = Decimal(0)

    token_map: list[tuple[int, str]] = [
        (input_tokens, TokenType.input.value),
        (output_tokens, TokenType.output.value),
        (cached_tokens, TokenType.cached_input.value),
        (reasoning_tokens, TokenType.reasoning.value),
    ]

    for count, ttype in token_map:
        if count <= 0:
            continue
        rate = pricing_cache.lookup(provider, model, ttype, timestamp)
        if rate is None:
            continue
        total += (Decimal(count) / million) * rate

    return total.quantize(Decimal("0.000001"))
