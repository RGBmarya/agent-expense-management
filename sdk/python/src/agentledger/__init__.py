"""AgentLedger -- AI expense management SDK.

Capture LLM token costs without a proxy.  Wraps OpenAI and Anthropic clients
to record usage events and batch-deliver them to the AgentLedger ingest API.

Quick start::

    import agentledger

    agentledger.init(api_key="ak_...", project="pa-processor", team="underwriting")
    agentledger.instrument()   # auto-patches OpenAI / Anthropic

    # -- or wrap individual clients --
    from agentledger.wrappers import wrap_openai
    from openai import OpenAI

    client = wrap_openai(OpenAI())
"""

from __future__ import annotations

import logging
from typing import List, Optional

from agentledger.config import AgentLedgerConfig, get_config, set_config
from agentledger.batcher import get_batcher, reset_batcher
from agentledger.events import UsageEvent, EventType
from agentledger.instrument import instrument as _instrument_fn

__version__ = "0.1.0"

__all__ = [
    "init",
    "instrument",
    "shutdown",
    "AgentLedgerConfig",
    "UsageEvent",
    "EventType",
    "__version__",
]

logger = logging.getLogger("agentledger")


def init(
    *,
    api_key: str = "",
    project: str = "",
    team: str = "",
    environment: str = "default",
    endpoint: Optional[str] = None,
    batch_size: int = 100,
    flush_interval_s: float = 5.0,
    max_buffer_size: int = 1000,
    max_retries: int = 2,
    enabled: bool = True,
    debug: bool = False,
) -> AgentLedgerConfig:
    """Initialise the AgentLedger SDK.

    Must be called before any LLM clients are wrapped.  Parameters can also
    be supplied via environment variables (``AGENTLEDGER_API_KEY``, etc.) --
    explicit arguments take precedence.

    Parameters
    ----------
    api_key:
        API key for authenticating with the AgentLedger ingest API.
    project:
        Logical project name (e.g. ``"pa-processor"``).
    team:
        Team that owns the project (e.g. ``"underwriting"``).
    environment:
        Deployment environment (e.g. ``"production"``, ``"staging"``).
    endpoint:
        Override the default AgentLedger ingest API base URL.
    batch_size:
        Number of events that triggers an automatic flush.
    flush_interval_s:
        Seconds between periodic background flushes.
    max_buffer_size:
        Maximum events held in memory before oldest are dropped.
    max_retries:
        Retry attempts for failed HTTP flushes.
    enabled:
        Master kill-switch.  Set to ``False`` to disable all capture.
    debug:
        Enable verbose diagnostic logging.

    Returns
    -------
    The :class:`AgentLedgerConfig` instance that was created.
    """
    kwargs: dict = dict(
        api_key=api_key,
        project=project,
        team=team,
        environment=environment,
        batch_size=batch_size,
        flush_interval_s=flush_interval_s,
        max_buffer_size=max_buffer_size,
        max_retries=max_retries,
        enabled=enabled,
        debug=debug,
    )
    if endpoint is not None:
        kwargs["endpoint"] = endpoint

    config = AgentLedgerConfig(**kwargs)

    warnings = config.validate()
    for w in warnings:
        logger.warning("agentledger: config warning -- %s", w)

    if config.debug:
        logging.getLogger("agentledger").setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[agentledger] %(message)s"))
        logging.getLogger("agentledger").addHandler(handler)

    # Reset any existing batcher so it picks up the new config.
    reset_batcher()
    set_config(config)

    return config


def instrument() -> List[str]:
    """Auto-instrument all detected LLM provider libraries.

    Call this after :func:`init`.  Returns a list of provider names that were
    successfully patched (e.g. ``["openai", "anthropic"]``).
    """
    return _instrument_fn()


def shutdown() -> None:
    """Flush pending events and shut down background threads.

    Call this during application teardown to ensure no events are lost.
    An ``atexit`` handler also calls this automatically, but explicit
    shutdown is recommended for long-running services.
    """
    try:
        get_batcher().shutdown()
    except Exception:
        logger.debug("agentledger: error during shutdown", exc_info=True)
