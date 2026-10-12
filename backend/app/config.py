from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable fallback and local defaults."""

    APP_NAME: str = "ResolveAI"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database URL: default stores SQLite file inside backend/data/resolveai.db
    DATABASE_URL: str = "sqlite:///./data/resolveai.db"

    # CORS origins allowed in local development
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
