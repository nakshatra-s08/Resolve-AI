from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.config import get_settings
from app.database import init_db, SessionLocal
from app.services.policy_seed import seed_policy_library

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is initialized on application startup
    init_db()
    # Idempotently seed curated policy library into SQLite
    db = SessionLocal()
    try:
        seed_policy_library(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "ResolveAI backend API — Personal repair-resolution agent "
        "managing consumer repair cases, evidence, policy retrieval, and actions."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS conservatively for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Include API routes under /api
app.include_router(api_router)
