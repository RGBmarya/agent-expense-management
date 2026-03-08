"""AgentLedger SDK configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


_DEFAULT_ENDPOINT = "https://api.agentledger.dev"
_DEFAULT_BATCH_SIZE = 100
_DEFAULT_FLUSH_INTERVAL_S = 5.0
_DEFAULT_MAX_BUFFER_SIZE = 1000
_DEFAULT_MAX_RETRIES = 2


@dataclass(frozen=False)
class AgentLedgerConfig:
    """Holds all configuration for the AgentLedger SDK.

    Attributes:
        api_key: API key for authenticating with the AgentLedger ingest API.
        project: Logical project name (e.g. "pa-processor").
        team: Team that owns the project (e.g. "underwriting").
        environment: Deployment environment (e.g. "production", "staging").
        endpoint: Base URL of the AgentLedger ingest API.
        batch_size: Number of events that triggers an automatic flush.
        flush_interval_s: Seconds between periodic background flushes.
        max_buffer_size: Maximum events held in memory. When exceeded the oldest
            events are dropped (never backpressure).
        max_retries: Number of retry attempts for failed HTTP flushes.
        enabled: Master kill-switch. When ``False`` no events are captured.
        debug: When ``True`` logs diagnostic information to stderr.
    """

    api_key: str = ""
    project: str = ""
    team: str = ""
    environment: str = "default"
    endpoint: str = field(default_factory=lambda: os.getenv(
        "AGENTLEDGER_ENDPOINT", _DEFAULT_ENDPOINT
    ))
    batch_size: int = _DEFAULT_BATCH_SIZE
    flush_interval_s: float = _DEFAULT_FLUSH_INTERVAL_S
    max_buffer_size: int = _DEFAULT_MAX_BUFFER_SIZE
    max_retries: int = _DEFAULT_MAX_RETRIES
    enabled: bool = True
    debug: bool = False

    def __post_init__(self) -> None:
        # Allow environment variable overrides.
        self.api_key = self.api_key or os.getenv("AGENTLEDGER_API_KEY", "")
        self.project = self.project or os.getenv("AGENTLEDGER_PROJECT", "")
        self.team = self.team or os.getenv("AGENTLEDGER_TEAM", "")
        self.environment = self.environment or os.getenv("AGENTLEDGER_ENVIRONMENT", "default")
        if os.getenv("AGENTLEDGER_DEBUG", "").lower() in ("1", "true", "yes"):
            self.debug = True

    @property
    def ingest_url(self) -> str:
        """Full URL for the event ingest endpoint."""
        return f"{self.endpoint.rstrip('/')}/v1/events"

    def validate(self) -> list[str]:
        """Return a list of validation warnings (empty when config is valid)."""
        warnings: list[str] = []
        if not self.api_key:
            warnings.append("api_key is not set")
        if not self.project:
            warnings.append("project is not set")
        return warnings


# Module-level singleton used by the rest of the SDK.
_global_config: Optional[AgentLedgerConfig] = None


def get_config() -> AgentLedgerConfig:
    """Return the global configuration, creating a default one if needed."""
    global _global_config
    if _global_config is None:
        _global_config = AgentLedgerConfig()
    return _global_config


def set_config(config: AgentLedgerConfig) -> None:
    """Replace the global configuration."""
    global _global_config
    _global_config = config
