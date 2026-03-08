"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Core ---
    DATABASE_URL: str  # required – no default; set via env var or .env file
    SECRET_KEY: str  # required – no default; set via env var or .env file
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    # --- SMTP (optional) ---
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None

    # --- Slack (optional) ---
    SLACK_WEBHOOK: str | None = None

    # --- Stripe Issuing (optional) ---
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    CARD_ENCRYPTION_KEY: str | None = None  # 32-byte hex for AES-256-GCM


settings = Settings()
