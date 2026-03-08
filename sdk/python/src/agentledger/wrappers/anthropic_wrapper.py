"""Anthropic client wrapper for AgentLedger.

Monkey-patches ``messages.create`` (and its async counterpart) to capture
token usage.  Handles both regular and streaming responses, and extracts
Anthropic-specific cached-token fields (``cache_read_input_tokens`` and
``cache_creation_input_tokens``) from the usage object.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Iterator, AsyncIterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger("agentledger.wrappers.anthropic")


def wrap_anthropic(client: Any) -> Any:
    """Instrument an Anthropic client instance *in place*.

    Works with both ``anthropic.Anthropic`` and ``anthropic.AsyncAnthropic``.

    Parameters
    ----------
    client:
        An ``anthropic.Anthropic`` or ``anthropic.AsyncAnthropic`` instance.

    Returns
    -------
    The same *client* reference (for convenience chaining).
    """
    try:
        messages = client.messages
    except AttributeError:
        logger.debug("agentledger: client has no messages attribute; skipping wrap")
        return client

    # Guard against double-wrapping.
    if getattr(messages.create, "_agentledger_wrapped", False):
        return client

    original_create = messages.create

    import asyncio

    if asyncio.iscoroutinefunction(original_create):
        _patch_async_create(messages, original_create)
    else:
        _patch_sync_create(messages, original_create)

    # Also patch the stream() context manager if available.
    if hasattr(messages, "stream"):
        original_stream = messages.stream
        if not getattr(original_stream, "_agentledger_wrapped", False):
            if asyncio.iscoroutinefunction(original_stream):
                _patch_async_stream(messages, original_stream)
            else:
                _patch_sync_stream(messages, original_stream)

    return client


# ---------------------------------------------------------------------------
# Shared stream interceptor logic (sync + async)
# ---------------------------------------------------------------------------


class _StreamInterceptorBase:
    """Shared init, extract, and emit logic for stream interceptors."""

    def __init__(self, stream: Any, kwargs: dict[str, Any], start: float) -> None:
        self._stream = stream
        self._kwargs = kwargs
        self._start = start
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._cached_tokens: int = 0
        self._cache_creation_tokens: int = 0
        self._model: Optional[str] = None

    def _extract_from_event(self, event: Any) -> None:
        """Pull usage data from Anthropic streaming events."""
        event_type = getattr(event, "type", "")

        if event_type == "message_start":
            message = getattr(event, "message", None)
            if message:
                self._model = getattr(message, "model", None)
                usage = getattr(message, "usage", None)
                if usage:
                    self._input_tokens = getattr(usage, "input_tokens", 0) or 0
                    self._cached_tokens = (
                        getattr(usage, "cache_read_input_tokens", 0) or 0
                    )
                    self._cache_creation_tokens = (
                        getattr(usage, "cache_creation_input_tokens", 0) or 0
                    )

        elif event_type == "message_delta":
            usage = getattr(event, "usage", None)
            if usage:
                self._output_tokens = getattr(usage, "output_tokens", 0) or 0

    def _emit(self, latency_ms: float) -> None:
        if self._input_tokens or self._output_tokens:
            _record_usage_from_raw(
                input_tokens=self._input_tokens,
                output_tokens=self._output_tokens,
                cached_tokens=self._cached_tokens,
                cache_creation_tokens=self._cache_creation_tokens,
                model=self._model or self._kwargs.get("model", ""),
                kwargs=self._kwargs,
                latency_ms=latency_ms,
            )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


# ---------------------------------------------------------------------------
# Sync create
# ---------------------------------------------------------------------------


def _patch_sync_create(messages: Any, original: Any) -> None:
    """Replace ``messages.create`` with a synchronous wrapper."""

    @functools.wraps(original)
    def wrapped_create(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        stream = kwargs.get("stream", False)
        try:
            response = original(*args, **kwargs)
        except Exception:
            raise

        if stream:
            return _StreamInterceptor(response, kwargs, start)

        latency_ms = (time.perf_counter() - start) * 1000
        _record_usage(response, kwargs, latency_ms)
        return response

    wrapped_create._agentledger_wrapped = True  # type: ignore[attr-defined]
    messages.create = wrapped_create


class _StreamInterceptor(_StreamInterceptorBase):
    """Wraps a synchronous Anthropic streaming response."""

    def __iter__(self) -> Iterator[Any]:
        try:
            for event in self._stream:
                self._extract_from_event(event)
                yield event
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


# ---------------------------------------------------------------------------
# Sync stream() context manager
# ---------------------------------------------------------------------------


def _patch_sync_stream(messages: Any, original: Any) -> None:
    """Wrap the ``messages.stream()`` context-manager helper."""

    @functools.wraps(original)
    def wrapped_stream(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            ctx = original(*args, **kwargs)
        except Exception:
            raise
        return _MessageStreamContextManager(ctx, kwargs, start)

    wrapped_stream._agentledger_wrapped = True  # type: ignore[attr-defined]
    messages.stream = wrapped_stream


class _MessageStreamContextManager:
    """Wraps Anthropic's ``MessageStream`` context manager to capture usage."""

    def __init__(self, ctx: Any, kwargs: dict[str, Any], start: float) -> None:
        self._ctx = ctx
        self._kwargs = kwargs
        self._start = start

    def __enter__(self) -> Any:
        stream = self._ctx.__enter__()
        return _MessageStreamProxy(stream, self._kwargs, self._start)

    def __exit__(self, *exc: Any) -> Any:
        return self._ctx.__exit__(*exc)


class _MessageStreamProxy:
    """Proxy around Anthropic's ``MessageStream`` that records usage on close."""

    def __init__(self, stream: Any, kwargs: dict[str, Any], start: float) -> None:
        self._stream = stream
        self._kwargs = kwargs
        self._start = start

    def __iter__(self) -> Iterator[Any]:
        return iter(self._stream)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    def get_final_message(self) -> Any:
        """Delegate and capture usage from the final message."""
        message = self._stream.get_final_message()
        latency_ms = (time.perf_counter() - self._start) * 1000
        _record_usage(message, self._kwargs, latency_ms)
        return message


# ---------------------------------------------------------------------------
# Async create
# ---------------------------------------------------------------------------


def _patch_async_create(messages: Any, original: Any) -> None:
    """Replace ``messages.create`` with an async wrapper."""

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
    messages.create = wrapped_create


class _AsyncStreamInterceptor(_StreamInterceptorBase):
    """Async counterpart of :class:`_StreamInterceptor`."""

    async def __aiter__(self) -> AsyncIterator[Any]:
        try:
            async for event in self._stream:
                self._extract_from_event(event)
                yield event
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


# ---------------------------------------------------------------------------
# Async stream() context manager
# ---------------------------------------------------------------------------


def _patch_async_stream(messages: Any, original: Any) -> None:
    """Wrap the async ``messages.stream()`` helper."""

    @functools.wraps(original)
    async def wrapped_stream(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            ctx = await original(*args, **kwargs)
        except Exception:
            raise
        return _AsyncMessageStreamContextManager(ctx, kwargs, start)

    wrapped_stream._agentledger_wrapped = True  # type: ignore[attr-defined]
    messages.stream = wrapped_stream


class _AsyncMessageStreamContextManager:
    """Async wrapper around Anthropic's ``AsyncMessageStream`` context manager."""

    def __init__(self, ctx: Any, kwargs: dict[str, Any], start: float) -> None:
        self._ctx = ctx
        self._kwargs = kwargs
        self._start = start

    async def __aenter__(self) -> Any:
        stream = await self._ctx.__aenter__()
        return _AsyncMessageStreamProxy(stream, self._kwargs, self._start)

    async def __aexit__(self, *exc: Any) -> Any:
        return await self._ctx.__aexit__(*exc)


class _AsyncMessageStreamProxy:
    """Async proxy that records usage on close."""

    def __init__(self, stream: Any, kwargs: dict[str, Any], start: float) -> None:
        self._stream = stream
        self._kwargs = kwargs
        self._start = start

    async def __aiter__(self) -> AsyncIterator[Any]:
        async for event in self._stream:
            yield event

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)

    async def get_final_message(self) -> Any:
        """Delegate and capture usage from the final message."""
        message = await self._stream.get_final_message()
        latency_ms = (time.perf_counter() - self._start) * 1000
        _record_usage(message, self._kwargs, latency_ms)
        return message


# ---------------------------------------------------------------------------
# Usage extraction
# ---------------------------------------------------------------------------


def _record_usage(response: Any, kwargs: dict[str, Any], latency_ms: float) -> None:
    """Extract usage from a non-streaming Anthropic response."""
    try:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        cached_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_creation_tokens = getattr(usage, "cache_creation_input_tokens", 0) or 0
        model = getattr(response, "model", "") or kwargs.get("model", "")

        _record_usage_from_raw(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cache_creation_tokens=cache_creation_tokens,
            model=model,
            kwargs=kwargs,
            latency_ms=latency_ms,
        )
    except Exception:
        logger.debug("agentledger: failed to record Anthropic usage", exc_info=True)


def _record_usage_from_raw(
    *,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    cache_creation_tokens: int,
    model: str,
    kwargs: dict[str, Any],
    latency_ms: float,
) -> None:
    """Build and enqueue a :class:`UsageEvent` from raw Anthropic usage data."""
    try:
        from agentledger.config import get_config
        from agentledger.batcher import get_batcher
        from agentledger.events import UsageEvent

        config = get_config()

        custom_tags: dict[str, Any] = {}
        if cache_creation_tokens > 0:
            custom_tags["cache_creation_input_tokens"] = cache_creation_tokens

        event = UsageEvent(
            provider="anthropic",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            latency_ms=latency_ms,
            environment=config.environment,
            team=config.team,
            project=config.project,
            custom_tags=custom_tags,
        )

        get_batcher().enqueue(event)
    except Exception:
        logger.debug("agentledger: failed to record Anthropic usage", exc_info=True)
