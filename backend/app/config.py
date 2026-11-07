from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable fallback and local defaults."""

    APP_NAME: str = "ResolveAI"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database URL: default stores SQLite file inside backend/data/resolveai.db
    DATABASE_URL: str = "sqlite:///./data/resolveai.db"

    # Uploads configuration
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    UPLOAD_STORAGE_BACKEND: str = "local"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "case-evidence"

    # AI Reasoning Provider Configuration
    # Supported providers: "demo", "ollama", "openai", "gemini"
    AI_PROVIDER: str = "demo"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0
    OLLAMA_CONNECT_TIMEOUT_SECONDS: float = 5.0
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # Gnani Prisma Speech-to-Text Configuration
    # Server-side API key for Gnani Prisma STT (vachana.ai)
    # Add GNANI_PRISMA_API_KEY to your local backend/.env or .env file
    GNANI_PRISMA_API_KEY: Optional[str] = None
    GNANI_PRISMA_BASE_URL: str = "https://api.vachana.ai"
    GNANI_PRISMA_MODEL: str = "prisma-v3.0"
    GNANI_PRISMA_LANGUAGE_CODE: str = "indic-auto"
    GNANI_PRISMA_TIMEOUT_SECONDS: float = 30.0

    # CORS origins allowed in local development
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
