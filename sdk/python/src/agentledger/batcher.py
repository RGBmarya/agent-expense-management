"""Async event batcher for AgentLedger.

Design goals
------------
* **Zero back-pressure** -- when the in-memory buffer is full the *oldest*
  events are silently dropped.
* **Non-blocking** -- callers enqueue events synchronously; a daemon thread
  handles HTTP delivery.
* **Graceful degradation** -- network / server errors are retried with
  exponential back-off and then silently discarded.  The host application's
  LLM calls are never affected.
"""

from __future__ import annotations

import atexit
import logging
import sys
import threading
import time
from collections import deque
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

import httpx

if TYPE_CHECKING:
    from agentledger.config import AgentLedgerConfig
    from agentledger.events import UsageEvent

logger = logging.getLogger("agentledger.batcher")


class EventBatcher:
    """Thread-safe, bounded event batcher with periodic flushing.

    Parameters
    ----------
    config:
        An :class:`AgentLedgerConfig` instance that supplies endpoint URL,
        API key, batch thresholds, and retry settings.
    """

    def __init__(self, config: AgentLedgerConfig) -> None:
        self._config = config

        # Bounded buffer -- oldest events are dropped on overflow.
        self._buffer: deque[Dict] = deque(maxlen=config.max_buffer_size)
        self._lock = threading.Lock()

        # Background flush thread.
        self._stop_event = threading.Event()
        self._flush_event = threading.Event()  # separate event for flush wakeup
        self._flush_thread: Optional[threading.Thread] = None
        self._started = False

        # HTTP client (lazy, created on first flush).
        self._http_client: Optional[httpx.Client] = None

        # Register an atexit handler so pending events are flushed on
        # interpreter shutdown.
        atexit.register(self._shutdown)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(self, event: UsageEvent) -> None:
        """Add an event to the buffer.

        This method is safe to call from any thread and *never* raises.
        """
        if not self._config.enabled:
            return
        try:
            payload = event.to_ingest_dict()
            with self._lock:
                # deque(maxlen=N) automatically drops the left-most (oldest)
                # item when appending beyond capacity.
                self._buffer.append(payload)
                buffer_len = len(self._buffer)

            # Ensure the background thread is running.
            self._ensure_started()

            # Eager flush when we hit the batch threshold.
            if buffer_len >= self._config.batch_size:
                self._trigger_flush()
        except Exception:
            # Never propagate errors to the caller.
            logger.debug("agentledger: failed to enqueue event", exc_info=True)

    def flush(self) -> None:
        """Synchronously flush all buffered events *right now*.

        Safe to call manually; also called by the background thread and
        the atexit handler.
        """
        events = self._drain_buffer()
        if not events:
            return
        self._send_batch(events)

    def shutdown(self) -> None:
        """Flush remaining events and stop the background thread."""
        self._shutdown()

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _ensure_started(self) -> None:
        if self._started:
            return
        with self._lock:
            if self._started:
                return
            self._flush_thread = threading.Thread(
                target=self._run_flush_loop, daemon=True, name="agentledger-batcher"
            )
            self._flush_thread.start()
            self._started = True

    def _run_flush_loop(self) -> None:
        """Periodically flush events until the stop event is set."""
        while not self._stop_event.is_set():
            try:
                self.flush()
            except Exception:
                logger.debug("agentledger: flush loop error", exc_info=True)
            # Wait for the flush interval, but wake on flush or stop signal.
            self._flush_event.wait(timeout=self._config.flush_interval_s)
            self._flush_event.clear()

    def _trigger_flush(self) -> None:
        """Request an immediate flush from the background thread."""
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_event.set()

    # ------------------------------------------------------------------
    # Buffer helpers
    # ------------------------------------------------------------------

    def _drain_buffer(self) -> List[Dict]:
        """Atomically drain all events from the buffer."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    # ------------------------------------------------------------------
    # HTTP transport
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.Client:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
            )
        return self._http_client

    def _send_batch(self, events: Sequence[Dict]) -> None:
        """POST a batch of events to the ingest API with retries.

        Failures are logged at debug level and silently discarded -- the host
        application must never be affected.
        """
        if not events:
            return

        url = self._config.ingest_url
        headers = {
            "X-API-Key": self._config.api_key,
            "Content-Type": "application/json",
            "User-Agent": "agentledger-python/0.1.0",
        }
        body = {"events": list(events)}

        last_exc: Optional[Exception] = None
        for attempt in range(1 + self._config.max_retries):
            try:
                client = self._get_client()
                response = client.post(url, json=body, headers=headers)
                if response.status_code < 400:
                    if self._config.debug:
                        logger.info(
                            "agentledger: flushed %d events (HTTP %d)",
                            len(events),
                            response.status_code,
                        )
                    return
                # 4xx (except 429) -- no point retrying.
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    logger.debug(
                        "agentledger: ingest rejected batch (HTTP %d): %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return
                last_exc = Exception(f"HTTP {response.status_code}")
            except Exception as exc:
                last_exc = exc

            # Exponential back-off: 0.5s, 1s, 2s ...
            if attempt < self._config.max_retries:
                backoff = 0.5 * (2 ** attempt)
                time.sleep(backoff)

        logger.debug(
            "agentledger: failed to flush %d events after %d attempts: %s",
            len(events),
            1 + self._config.max_retries,
            last_exc,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _shutdown(self) -> None:
        """Flush remaining events and tear down resources."""
        self._stop_event.set()
        self._flush_event.set()  # wake the flush loop so it exits
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)
        try:
            self.flush()
        except Exception:
            pass
        if self._http_client and not self._http_client.is_closed:
            try:
                self._http_client.close()
            except Exception:
                pass
        self._started = False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_global_batcher: Optional[EventBatcher] = None
_batcher_lock = threading.Lock()


def get_batcher() -> EventBatcher:
    """Return (and lazily create) the global batcher singleton."""
    global _global_batcher
    if _global_batcher is None:
        with _batcher_lock:
            if _global_batcher is None:
                from agentledger.config import get_config

                _global_batcher = EventBatcher(get_config())
    return _global_batcher


def set_batcher(batcher: EventBatcher) -> None:
    """Replace the global batcher (useful for testing)."""
    global _global_batcher
    _global_batcher = batcher


def reset_batcher() -> None:
    """Shutdown and remove the global batcher."""
    global _global_batcher
    if _global_batcher is not None:
        _global_batcher.shutdown()
        _global_batcher = None
