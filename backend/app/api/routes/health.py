from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.config import get_settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str


class AIDiagnosticsResponse(BaseModel):
    provider: str
    model: Optional[str] = None
    status: str


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Confirm backend application is operational."""
    return HealthResponse(status="ok")


@router.get("/diagnostics/ai", response_model=AIDiagnosticsResponse)
def get_ai_diagnostics() -> AIDiagnosticsResponse:
    """Report active AI provider configuration without exposing credentials."""
    settings = get_settings()
    provider_name = (settings.AI_PROVIDER or "demo").strip().lower()
    model = settings.OLLAMA_MODEL if provider_name == "ollama" else None
    return AIDiagnosticsResponse(
        provider=provider_name,
        model=model,
        status="configured",
    )
