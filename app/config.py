"""
OMNIA Configuration
Loads environment variables and provides typed settings.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

# Compute absolute path to .env
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "OMNIA"
    app_env: str = "development"
    secret_key: str = "change-me-to-a-secure-random-string"
    debug: bool = True

    # ── Database ─────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./omnia.db"

    # ── LLM APIs ─────────────────────────────────────────────
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    default_llm_provider: str = "groq"  # "gemini", "openai", or "groq"

    # ── Google Cloud ─────────────────────────────────────────
    google_maps_api_key: Optional[str] = None
    google_calendar_credentials_path: Optional[str] = None

    # ── Web Search ───────────────────────────────────────────
    tavily_api_key: Optional[str] = None

    # ── Voice ────────────────────────────────────────────────
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # ── Communication ────────────────────────────────────────
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    whatsapp_api_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    jwt_refresh_expiration_days: int = 7

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def active_llm_provider(self) -> str:
        """Returns the active LLM provider, falling back if primary is unavailable."""
        if self.default_llm_provider == "groq" and self.has_groq:
            return "groq"
        elif self.default_llm_provider == "gemini" and self.has_gemini:
            return "gemini"
        elif self.default_llm_provider == "openai" and self.has_openai:
            return "openai"
        elif self.has_groq:
            return "groq"
        elif self.has_gemini:
            return "gemini"
        elif self.has_openai:
            return "openai"
        return "none"


# Singleton settings instance
settings = Settings()
