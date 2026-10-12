from fastapi import APIRouter
from app.api.routes import health, cases, evidence, policies, analysis

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(cases.router)
api_router.include_router(evidence.router)
api_router.include_router(policies.router)
api_router.include_router(analysis.router)
