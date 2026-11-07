import httpx
import pytest
from fastapi import HTTPException

from app import database
from app.config import get_settings
from app.services import storage


@pytest.mark.asyncio
async def test_supabase_upload_keeps_credentials_server_side(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setattr(settings, "SUPABASE_STORAGE_BUCKET", "case-evidence")

    captured = {}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, headers, content):
            captured.update(url=url, headers=headers, content=content)
            return httpx.Response(200)

    monkeypatch.setattr(storage.httpx, "AsyncClient", lambda **_kwargs: FakeAsyncClient())

    await storage._upload_to_supabase("sample.pdf", b"%PDF-test", "application/pdf")

    assert captured["url"] == "https://example.supabase.co/storage/v1/object/case-evidence/uploads/sample.pdf"
    assert captured["headers"]["Authorization"] == "Bearer test-service-role-key"
    assert captured["headers"]["x-upsert"] == "false"
    assert captured["content"] == b"%PDF-test"


def test_supabase_evidence_delete_can_be_rolled_back(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setattr(settings, "SUPABASE_STORAGE_BUCKET", "case-evidence")
    calls = []

    def fake_request(method, url, headers, json=None):
        calls.append((method, url, json))
        return httpx.Response(200)

    monkeypatch.setattr(storage, "_supabase_request", fake_request)

    staged_name = storage.stage_stored_file_for_deletion("sample.pdf")
    assert staged_name and staged_name.startswith(".deleting-")
    assert storage.restore_staged_file("sample.pdf", staged_name)
    assert storage.discard_staged_file(staged_name)

    assert calls[0][0] == "POST"
    assert calls[0][2] == {
        "bucketId": "case-evidence",
        "sourceKey": "uploads/sample.pdf",
        "destinationKey": f"uploads/{staged_name}",
    }
    assert calls[1][2]["sourceKey"] == f"uploads/{staged_name}"
    assert calls[1][2]["destinationKey"] == "uploads/sample.pdf"
    assert calls[2][0] == "DELETE"
    assert calls[2][2] == {"prefixes": [f"uploads/{staged_name}"]}


def test_database_url_uses_psycopg_for_hosted_postgres():
    assert database.normalize_database_url("postgres://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"
    assert database.normalize_database_url("postgresql://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"
    assert database.normalize_database_url("sqlite:///./data/test.db") == "sqlite:///./data/test.db"


def test_vercel_rejects_non_persistent_sqlite(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")

    with pytest.raises(RuntimeError, match="hosted DATABASE_URL"):
        database.init_db()


def test_vercel_rejects_local_evidence_storage(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("VERCEL", "1")

    with pytest.raises(HTTPException, match="Vercel evidence uploads require Supabase Storage"):
        storage._storage_backend()
