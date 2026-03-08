"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Core ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentledger"
    SECRET_KEY: str  # required – no default; set via env var or .env file
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- SMTP (optional) ---
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None

    # --- Slack (optional) ---
    SLACK_WEBHOOK: str | None = None


settings = Settings()
