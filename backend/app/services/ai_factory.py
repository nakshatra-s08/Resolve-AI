from fastapi import HTTPException, status
from app.config import get_settings
from app.services.ai_provider import BaseAIProvider, DemoAIProvider, OllamaAIProvider


def get_ai_provider() -> BaseAIProvider:
    """Return configured AI provider (demo, ollama) or fail clearly without silent fallback."""
    settings = get_settings()
    provider_name = (settings.AI_PROVIDER or "demo").strip().lower()
    if provider_name == "demo":
        return DemoAIProvider()

    if provider_name == "ollama":
        provider = OllamaAIProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            connect_timeout=settings.OLLAMA_CONNECT_TIMEOUT_SECONDS,
        )
        is_healthy, err_msg = provider.check_health()
        if not is_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=err_msg,
            )
        return provider

    if provider_name not in {"openai", "gemini"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI_PROVIDER must be 'demo', 'ollama', 'openai', or 'gemini'.",
        )

    key = settings.OPENAI_API_KEY if provider_name == "openai" else settings.GEMINI_API_KEY
    if not key:
        # Keep documented offline fallback when credentials are absent for cloud providers.
        return DemoAIProvider()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"The configured {provider_name} provider is not implemented; use AI_PROVIDER=demo or AI_PROVIDER=ollama.",
    )
