import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.config import get_settings
from app.services.policy_seed import seed_policy_library

# Use an in-memory SQLite database isolated per test session with StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_test,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in the isolated test database and seed policy library."""
    Base.metadata.create_all(bind=engine_test)
    init_session = TestingSessionLocal()
    seed_policy_library(init_session)
    init_session.close()
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(autouse=True)
def isolated_upload_dir(monkeypatch):
    """Ensure all file uploads during testing happen in an isolated temporary directory."""
    temp_dir = tempfile.mkdtemp()
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", temp_dir)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Provide a clean database session per test by clearing tables between runs."""
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session, monkeypatch) -> Generator[TestClient, None, None]:
    """TestClient wired with database session override."""
    @asynccontextmanager
    async def isolated_lifespan(application):
        # App startup uses the production engine directly; tests must never touch it.
        yield

    monkeypatch.setattr(app.router, "lifespan_context", isolated_lifespan)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
