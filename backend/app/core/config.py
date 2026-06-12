from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://microhabit:microhabit@127.0.0.1:5432/microhabit"

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        # Render (and many other hosts) provide postgres:// or postgresql:// URLs.
        # SQLAlchemy async requires postgresql+asyncpg://.
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    create_tables_on_startup: bool = True

    # Optional — when absent the AI endpoint falls back to the keyword engine.
    openai_api_key: str = ""

    # Auth — JWT signing key and token lifetime.
    # Generate a strong secret: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15

    # Google Calendar — read-only availability integration (v3.0).
    # All three OAuth vars must be non-empty to enable calendar features.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/calendar/auth/callback"
    # Where to send the browser after OAuth completes.
    frontend_url: str = "http://localhost:3000"
    # Fernet key for encrypting stored OAuth tokens. Required when calendar is enabled.
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    calendar_encryption_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
