from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart IT Helpdesk Management System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Database Settings (used only when DATABASE_URL is not set)
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "smart_helpdesk"
    DB_USER: str = "helpdesk_app"
    DB_PASSWORD: str = "helpdesk_secure_pass_phase2"
    DB_SSLMODE: str = "prefer"
    DATABASE_URL: Union[str, None] = None

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-this-to-a-long-random-secret-min-32-chars-dev-only"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Password Reset
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Frontend URL for email links
    FRONTEND_URL: str = "http://localhost:5173"

    # n8n Email Automation
    N8N_EMAIL_WEBHOOK_URL: str = ""
    N8N_EMAIL_WEBHOOK_SECRET: str = ""
    EMAIL_SENDER_NAME: str = "Smart IT Helpdesk"
    EMAIL_TIMEOUT_SECONDS: int = 10

    @field_validator("DEBUG", mode="before")
    def parse_debug(cls, v):
        if isinstance(v, str):
            val = v.strip().lower()
            if val in ("release", "prod", "production", "false", "0", "no", "off"):
                return False
            if val in ("debug", "dev", "development", "true", "1", "yes", "on"):
                return True
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def sync_database_url(self) -> str:
        """
        Return a SQLAlchemy-compatible connection URL for psycopg (v3).

        Railway and some other providers emit  postgres://  (without '+psycopg' and
        sometimes with the legacy  postgres  scheme).  Normalise both so the driver
        always receives  postgresql+psycopg://  regardless of source.
        """
        raw = self.DATABASE_URL
        if raw:
            # 1. postgres:// → postgresql://  (legacy scheme emitted by some providers)
            if raw.startswith("postgres://"):
                raw = "postgresql" + raw[len("postgres"):]
            # 2. postgresql:// → postgresql+psycopg://  (add psycopg3 dialect)
            if raw.startswith("postgresql://"):
                raw = "postgresql+psycopg" + raw[len("postgresql"):]
            return raw
        # Fall back to individual host/port/name settings (local dev only)
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
