"""OpenAI client wrapper for AgentLedger.

Monkey-patches ``chat.completions.create`` (and its async counterpart) to
capture token usage without altering the response seen by the caller.

Handles both streaming and non-streaming responses, and extracts cached-token
counts from ``usage.prompt_tokens_details`` when the provider includes them.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Iterator, AsyncIterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("agentledger.wrappers.openai")


def wrap_openai(client: Any) -> Any:
    """Instrument an OpenAI client instance *in place*.

    Works with both ``openai.OpenAI`` and ``openai.AsyncOpenAI``.  The
    original ``chat.completions.create`` method is replaced by a thin wrapper
    that records token usage after every call.

    Parameters
    ----------
    client:
        An ``openai.OpenAI`` or ``openai.AsyncOpenAI`` instance.

    Returns
    -------
    The same *client* reference (for convenience chaining).
    """
    try:
        completions = client.chat.completions
    except AttributeError:
        logger.debug("agentledger: client has no chat.completions; skipping wrap")
        return client

    # Guard against double-wrapping.
    if getattr(completions.create, "_agentledger_wrapped", False):
        return client

    original_create = completions.create

    # Detect sync vs async client.
    import asyncio

    if asyncio.iscoroutinefunction(original_create):
        _patch_async_create(completions, original_create)
    else:
        _patch_sync_create(completions, original_create)

    return client


# ---------------------------------------------------------------------------
# Sync path
# ---------------------------------------------------------------------------


def _patch_sync_create(completions: Any, original: Any) -> None:
    """Replace ``completions.create`` with a synchronous wrapper."""

    @functools.wraps(original)
    def wrapped_create(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        stream = kwargs.get("stream", False)
        try:
            response = original(*args, **kwargs)
        except Exception:
            # LLM calls must never be broken by our instrumentation.
            raise

        if stream:
            return _StreamInterceptor(response, kwargs, start)

        # Non-streaming: usage is available immediately.
        latency_ms = (time.perf_counter() - start) * 1000
        _record_usage(response, kwargs, latency_ms)
        return response

    wrapped_create._agentledger_wrapped = True  # type: ignore[attr-defined]
    completions.create = wrapped_create


class _StreamInterceptor:
    """Wraps a synchronous OpenAI streaming response.

    Transparently yields chunks to the caller while accumulating a final
    usage snapshot from the terminal chunk (when ``stream_options``
    includes ``{"include_usage": True}``).
    """

    def __init__(self, stream: Any, kwargs: dict[str, Any], start: float) -> None:
        self._stream = stream
        self._kwargs = kwargs
        self._start = start
        self._final_usage: Any = None
        self._model: Optional[str] = None

    def __iter__(self) -> Iterator[Any]:
        try:
            for chunk in self._stream:
                if hasattr(chunk, "model") and chunk.model:
                    self._model = chunk.model
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    self._final_usage = chunk.usage
                yield chunk
        finally:
            latency_ms = (time.perf_counter() - self._start) * 1000
            self._emit(latency_ms)

    def __enter__(self) -> _StreamInterceptor:
        if hasattr(self._stream, "__enter__"):
            self._stream.__enter__()
        return self

    def __exit__(self, *exc: Any) -> None:
        if hasattr(self._stream, "__exit__"):
            self._stream.__exit__(*exc)

    # Delegate attribute access to the underlying stream so callers that
    # inspect the response object still work.
    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    def _emit(self, latency_ms: float) -> None:
        if self._final_usage is not None:
            _record_usage_from_raw(
                usage=self._final_usage,
                model=self._model or self._kwargs.get("model", ""),
                kwargs=self._kwargs,
                latency_ms=latency_ms,
            )


# ---------------------------------------------------------------------------
# Async path
# ---------------------------------------------------------------------------


def _patch_async_create(completions: Any, original: Any) -> None:
    """Replace ``completions.create`` with an async wrapper."""

    @functools.wraps(original)
    async def wrapped_create(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        stream = kwargs.get("stream", False)
        try:
            response = await original(*args, **kwargs)
        except Exception:
            raise

        if stream:
            return _AsyncStreamInterceptor(response, kwargs, start)

        latency_ms = (time.perf_counter() - start) * 1000
        _record_usage(response, kwargs, latency_ms)
        return response

    wrapped_create._agentledger_wrapped = True  # type: ignore[attr-defined]
    completions.create = wrapped_create


class _AsyncStreamInterceptor:
    """Async counterpart of :class:`_StreamInterceptor`."""

    def __init__(self, stream: Any, kwargs: dict[str, Any], start: float) -> None:
        self._stream = stream
        self._kwargs = kwargs
        self._start = start
        self._final_usage: Any = None
        self._model: Optional[str] = None

    async def __aiter__(self) -> AsyncIterator[Any]:
        try:
            async for chunk in self._stream:
                if hasattr(chunk, "model") and chunk.model:
                    self._model = chunk.model
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    self._final_usage = chunk.usage
                yield chunk
        finally:
            latency_ms = (time.perf_counter() - self._start) * 1000
            self._emit(latency_ms)

    async def __aenter__(self) -> _AsyncStreamInterceptor:
        if hasattr(self._stream, "__aenter__"):
            await self._stream.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if hasattr(self._stream, "__aexit__"):
            await self._stream.__aexit__(*exc)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    def _emit(self, latency_ms: float) -> None:
        if self._final_usage is not None:
            _record_usage_from_raw(
                usage=self._final_usage,
                model=self._model or self._kwargs.get("model", ""),
                kwargs=self._kwargs,
                latency_ms=latency_ms,
            )


# ---------------------------------------------------------------------------
# Usage extraction
# ---------------------------------------------------------------------------


def _record_usage(response: Any, kwargs: dict[str, Any], latency_ms: float) -> None:
    """Extract usage from a non-streaming OpenAI response and enqueue an event."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        model = getattr(response, "model", "") or kwargs.get("model", "")
        _record_usage_from_raw(usage, model, kwargs, latency_ms)
    except Exception:
        logger.debug("agentledger: failed to record OpenAI usage", exc_info=True)


def _record_usage_from_raw(
    usage: Any,
    model: str,
    kwargs: dict[str, Any],
    latency_ms: float,
) -> None:
    """Build and enqueue a :class:`UsageEvent` from an OpenAI usage object."""
    try:
        from agentledger.config import get_config
        from agentledger.batcher import get_batcher
        from agentledger.events import UsageEvent

        config = get_config()

        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0

        # Cached tokens -- OpenAI puts these in prompt_tokens_details.
        cached_tokens = 0
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        if prompt_details is not None:
            cached_tokens = getattr(prompt_details, "cached_tokens", 0) or 0

        # Reasoning tokens -- available in completion_tokens_details.
        reasoning_tokens = 0
        completion_details = getattr(usage, "completion_tokens_details", None)
        if completion_details is not None:
            reasoning_tokens = getattr(completion_details, "reasoning_tokens", 0) or 0

        event = UsageEvent(
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            latency_ms=latency_ms,
            environment=config.environment,
            team=config.team,
            project=config.project,
        )

        get_batcher().enqueue(event)
    except Exception:
        logger.debug("agentledger: failed to record OpenAI usage", exc_info=True)
