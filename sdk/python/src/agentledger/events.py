"""Pydantic event models for AgentLedger.

The schema is intentionally extensible: ``custom_tags`` is an open dict and new
``event_type`` values can be added without breaking existing consumers.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Known event types. The field is a plain ``str`` on the model so unknown
    values coming from newer SDK versions are still accepted."""

    LLM_USAGE = "llm_usage"
    AGENT_TRANSACTION = "agent_transaction"


class UsageEvent(BaseModel):
    """A single usage / cost event emitted by an instrumented LLM call.

    Fields marked *optional* are populated only when the information is
    available from the provider response.
    """

    # ---- identity ----
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    idempotency_key: str = ""
    event_type: str = EventType.LLM_USAGE.value

    # ---- provider / model ----
    provider: str = ""
    model: str = ""

    # ---- timing ----
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    latency_ms: float = 0.0

    # ---- token counts ----
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0

    # ---- cost ----
    estimated_cost_usd: Optional[float] = None
    amount_usd: Optional[float] = None

    # ---- transaction / merchant (for agent_transaction events) ----
    merchant: Optional[str] = None
    transaction_hash: Optional[str] = None

    # ---- context ----
    environment: str = "default"
    team: str = ""
    project: str = ""
    agent_id: Optional[str] = None
    custom_tags: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Derive the idempotency key when not explicitly provided."""
        if not self.idempotency_key:
            self.idempotency_key = self._derive_idempotency_key()

    def _derive_idempotency_key(self) -> str:
        """Deterministic key based on the core event attributes.

        Two events with the same provider, model, token counts, timestamp, and
        project will produce the same key, enabling server-side dedup.
        """
        payload = (
            f"{self.provider}:{self.model}:{self.input_tokens}:"
            f"{self.output_tokens}:{self.timestamp}:{self.project}:{self.id}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:32]

    def to_ingest_dict(self) -> Dict[str, Any]:
        """Serialise the event for the ingest API.

        Excludes ``None`` values to keep payloads compact.
        """
        data = self.model_dump(exclude_none=True)
        return data
