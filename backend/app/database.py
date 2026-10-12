import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import get_settings

settings = get_settings()

DATABASE_URL = settings.DATABASE_URL


def ensure_sqlite_dir(url: str) -> None:
    """Ensure the directory for SQLite database files exists."""
    if url.startswith("sqlite:///"):
        db_path_str = url.replace("sqlite:///", "", 1)
        if db_path_str and db_path_str != ":memory:":
            db_path = Path(db_path_str)
            db_dir = db_path.parent
            if db_dir and not db_dir.exists():
                db_dir.mkdir(parents=True, exist_ok=True)


ensure_sqlite_dir(DATABASE_URL)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    # Ensure tables are registered on Base before creating
    import app.models  # noqa: F401
    ensure_sqlite_dir(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
