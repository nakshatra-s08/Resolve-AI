from fastapi import HTTPException, status
from app.config import get_settings
from app.services.ai_provider import BaseAIProvider, DemoAIProvider


def get_ai_provider() -> BaseAIProvider:
    """Return demo mode or fail clearly for an unavailable live provider."""
    settings = get_settings()
    provider_name = (settings.AI_PROVIDER or "demo").strip().lower()
    if provider_name == "demo":
        return DemoAIProvider()
    if provider_name not in {"openai", "gemini"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI_PROVIDER must be 'demo', 'openai', or 'gemini'.",
        )

    key = settings.OPENAI_API_KEY if provider_name == "openai" else settings.GEMINI_API_KEY
    if not key:
        # Keep the documented offline fallback when credentials are absent.
        return DemoAIProvider()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"The configured {provider_name} provider is not implemented; use AI_PROVIDER=demo.",
    )
