"""Auto-instrumentation for AgentLedger.

Detects which LLM provider libraries are installed and monkey-patches their
default client classes so that *any* instance created after
:func:`instrument` is called will automatically capture usage events.

This is the "zero-config" path -- users who want finer control should use
:func:`agentledger.wrappers.wrap_openai` / :func:`agentledger.wrappers.wrap_anthropic`
on individual client instances instead.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, List

logger = logging.getLogger("agentledger.instrument")

_instrumented: bool = False


def instrument() -> List[str]:
    """Auto-instrument all detected LLM provider libraries.

    Returns a list of provider names that were successfully instrumented.

    This function is idempotent -- calling it multiple times is safe and will
    not double-wrap.
    """
    global _instrumented
    if _instrumented:
        logger.debug("agentledger: already instrumented; skipping")
        return []

    patched: List[str] = []

    if _instrument_openai():
        patched.append("openai")

    if _instrument_anthropic():
        patched.append("anthropic")

    if patched:
        _instrumented = True
        logger.debug("agentledger: instrumented providers: %s", patched)
    else:
        logger.debug("agentledger: no supported providers detected")

    return patched


def _instrument_openai() -> bool:
    """Patch ``openai.OpenAI`` and ``openai.AsyncOpenAI`` __init__ methods."""
    try:
        openai = importlib.import_module("openai")
    except ImportError:
        return False

    from agentledger.wrappers.openai_wrapper import wrap_openai

    _patch_class_init(openai, "OpenAI", wrap_openai)
    _patch_class_init(openai, "AsyncOpenAI", wrap_openai)
    return True


def _instrument_anthropic() -> bool:
    """Patch ``anthropic.Anthropic`` and ``anthropic.AsyncAnthropic`` __init__ methods."""
    try:
        anthropic = importlib.import_module("anthropic")
    except ImportError:
        return False

    from agentledger.wrappers.anthropic_wrapper import wrap_anthropic

    _patch_class_init(anthropic, "Anthropic", wrap_anthropic)
    _patch_class_init(anthropic, "AsyncAnthropic", wrap_anthropic)
    return True


def _patch_class_init(module: Any, class_name: str, wrapper_fn: Any) -> None:
    """Monkey-patch ``__init__`` on *module.class_name* so that every new
    instance is automatically wrapped by *wrapper_fn*.

    The patch is idempotent: if the class has already been patched it is a
    no-op.
    """
    cls = getattr(module, class_name, None)
    if cls is None:
        return

    if getattr(cls, "_agentledger_auto_instrumented", False):
        return

    original_init = cls.__init__

    def patched_init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        try:
            wrapper_fn(self)
        except Exception:
            # Never break client construction.
            logger.debug(
                "agentledger: failed to auto-wrap %s.%s",
                module.__name__,
                class_name,
                exc_info=True,
            )

    cls.__init__ = patched_init
    cls._agentledger_auto_instrumented = True  # type: ignore[attr-defined]
