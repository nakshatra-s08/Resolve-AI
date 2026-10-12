from fastapi import APIRouter
from app.api.routes import health, cases, evidence

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(cases.router)
api_router.include_router(evidence.router)
