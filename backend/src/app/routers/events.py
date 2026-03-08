"""POST /v1/events – Ingest batched usage events."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_org
from app.cost_engine import compute_event_cost
from app.database import get_session
from app.models import Event, Organization
from app.schemas import EventBatchRequest, EventBatchResponse, EventResponse

router = APIRouter()


@router.post("/events", response_model=EventBatchResponse)
async def ingest_events(
    body: EventBatchRequest,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> EventBatchResponse:
    """Accept a batch of usage events.

    - Validates each event
    - Deduplicates by (org_id, idempotency_key)
    - Computes estimated_cost_usd from the pricing table
    - Persists to the events table
    """
    # Collect existing idempotency keys for this batch in one query
    incoming_keys = [e.idempotency_key for e in body.events]
    existing_result = await session.execute(
        select(Event.idempotency_key).where(
            Event.org_id == org.id,
            Event.idempotency_key.in_(incoming_keys),
        )
    )
    existing_keys: set[str] = {row[0] for row in existing_result.all()}

    accepted: list[Event] = []
    duplicates = 0

    for ev in body.events:
        if ev.idempotency_key in existing_keys:
            duplicates += 1
            continue

        # Compute cost
        estimated_cost = await compute_event_cost(
            session,
            provider=ev.provider,
            model=ev.model,
            timestamp=ev.timestamp,
            input_tokens=ev.input_tokens,
            output_tokens=ev.output_tokens,
            cached_tokens=ev.cached_tokens,
            reasoning_tokens=ev.reasoning_tokens,
        )

        event = Event(
            org_id=org.id,
            idempotency_key=ev.idempotency_key,
            event_type=ev.event_type,
            provider=ev.provider,
            model=ev.model,
            timestamp=ev.timestamp,
            input_tokens=ev.input_tokens,
            output_tokens=ev.output_tokens,
            cached_tokens=ev.cached_tokens,
            reasoning_tokens=ev.reasoning_tokens,
            latency_ms=ev.latency_ms,
            amount_usd=ev.amount_usd,
            merchant=ev.merchant,
            transaction_hash=ev.transaction_hash,
            environment=ev.environment,
            team=ev.team,
            project=ev.project,
            agent_id=ev.agent_id,
            custom_tags=ev.custom_tags,
            estimated_cost_usd=estimated_cost,
        )
        session.add(event)
        accepted.append(event)
        # Track the key so later items in the same batch are also deduped
        existing_keys.add(ev.idempotency_key)

    await session.flush()  # populate IDs

    return EventBatchResponse(
        accepted=len(accepted),
        duplicates=duplicates,
        events=[EventResponse.model_validate(e) for e in accepted],
    )
