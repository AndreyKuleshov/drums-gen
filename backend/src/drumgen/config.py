"""Application settings, read from the environment (12-factor style).

The backend was previously config-free; this is the single place that reads env
vars so the rest of the code stays pure. Values below are dev-safe defaults —
production overrides them via real environment variables / Coolify secrets.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — async SQLAlchemy URL. Local dev points at the throwaway dev
    # Postgres (docker-compose.dev.yml, port 55432); prod injects the shared
    # instance URL (schema `drumgen`) via env.
    database_url: str = "postgresql+asyncpg://drumgen:drumgen@localhost:55432/drumgen"

    # Auth / sessions
    secret_key: str = "dev-insecure-secret-change-me"
    cookie_name: str = "sid"
    cookie_secure: bool = False  # True in prod (HTTPS only)
    session_ttl_days: int = 30
    verify_token_ttl_hours: int = 48
    reset_token_ttl_hours: int = 2

    # Public base URL used to build links inside emails (verify / reset).
    public_base_url: str = "http://localhost:5173"

    # Email (generic SMTP adapter — Brevo in prod). When email_enabled is False,
    # messages are logged to the console instead of sent (local dev).
    email_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    email_from: str = "no-reply@rudiment.local"
    email_from_name: str = "Rudiment Engine"


@lru_cache
def get_settings() -> Settings:
    return Settings()
