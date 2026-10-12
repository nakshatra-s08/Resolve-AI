from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Confirm backend application is operational."""
    return HealthResponse(status="ok")
