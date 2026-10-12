from contextlib import asynccontextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models.case import Case
from app.models.event import CaseEvent, EventType
from app.models.evidence import Evidence
from app.models.policy import PolicySource
from app.services.policy_seed import seed_policy_library
from tests.test_evidence import create_minimal_pdf


def test_end_to_end_phase_1_to_4_survives_new_session(tmp_path, monkeypatch):
    """Run a complete synthetic repair workflow against disposable file-backed SQLite."""
    db_path = tmp_path / "audit.sqlite"
    upload_dir = tmp_path / "private-uploads"
    monkeypatch.setattr(get_settings(), "UPLOAD_DIR", str(upload_dir))

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    seed_session = Session()
    seed_policy_library(seed_session)
    seed_session.close()

    request_session = Session()

    def override_get_db():
        yield request_session

    @asynccontextmanager
    async def isolated_lifespan(application):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", isolated_lifespan)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            case_response = client.post(
                "/api/cases",
                json={
                    "title": "Repeated laptop display fault",
                    "product_name": "Synthetic Testbook",
                    "issue_description": "Display flicker returned after two service repairs.",
                },
            )
            assert case_response.status_code == 201
            case_id = case_response.json()["id"]
            assert client.get(f"/api/cases/{case_id}").status_code == 200

            patch_response = client.patch(
                f"/api/cases/{case_id}", json={"issue_description": "Flicker returned after two repairs."}
            )
            assert patch_response.status_code == 200
            assert client.patch(
                f"/api/cases/{case_id}/status", json={"status": "UNDER_REVIEW"}
            ).status_code == 200

            pdf_response = client.post(
                f"/api/cases/{case_id}/evidence",
                files={"file": ("repair_job_sheet.pdf", create_minimal_pdf("Repair job sheet visit one"), "application/pdf")},
                data={"evidence_type": "REPAIR_RECEIPT"},
            )
            assert pdf_response.status_code == 201
            assert pdf_response.json()["extraction_status"] == "COMPLETED"
            evidence_id = pdf_response.json()["id"]
            assert len(client.get(f"/api/cases/{case_id}/evidence").json()) == 1
            assert "REPAIR_RECEIPT" in client.get(f"/api/cases/{case_id}/evidence-checklist").json()["represented_categories"]
            assert any(
                event["event_type"] == "EVIDENCE_UPLOADED"
                for event in client.get(f"/api/cases/{case_id}/timeline").json()
            )

            search = client.post("/api/policies/search", json={"query": "repair job sheets repeated defect", "limit": 5})
            assert search.status_code == 200
            assert search.json()["total_results"] > 0

            analysis = client.post(f"/api/cases/{case_id}/analysis")
            assert analysis.status_code == 200
            result = analysis.json()
            assert result["engine_mode"] == "demo"
            assert "Synthetic Testbook" in result["summary"]
            assert result["supporting_policy_sources"]
            assert any(
                source["passage"][:100] in result["reasoning"]
                for source in result["supporting_policy_sources"]
            )
            assert client.get(f"/api/cases/{case_id}").json()["status"] == "UNDER_REVIEW"

            # Simulate a database failure during deletion and check that the staged
            # file is restored while its evidence row remains available.
            stored_path = next(upload_dir.iterdir())
            real_commit = request_session.commit

            def failed_commit():
                raise RuntimeError("synthetic commit failure")

            monkeypatch.setattr(request_session, "commit", failed_commit)
            failed_delete = client.delete(f"/api/cases/{case_id}/evidence/{evidence_id}")
            assert failed_delete.status_code == 500
            assert stored_path.exists()
            assert request_session.query(Evidence).filter_by(id=evidence_id).one()
            monkeypatch.setattr(request_session, "commit", real_commit)

        request_session.close()
        resumed = Session()
        assert resumed.query(Case).filter_by(id=case_id).one().product_name == "Synthetic Testbook"
        assert resumed.query(Evidence).filter_by(id=evidence_id).one().case_id == case_id
        events = resumed.query(CaseEvent).filter_by(case_id=case_id).order_by(CaseEvent.created_at, CaseEvent.id).all()
        assert any(event.event_type == EventType.EVIDENCE_UPLOADED for event in events)
        assert resumed.query(PolicySource).count() == 4
        resumed.close()
    finally:
        app.dependency_overrides.clear()
        request_session.close()
        engine.dispose()


def test_configured_live_provider_is_not_misreported_as_demo(monkeypatch):
    from fastapi import HTTPException
    from app.services.ai_factory import get_ai_provider

    settings = get_settings()
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    try:
        get_ai_provider()
        assert False, "A configured but unimplemented live provider must fail clearly"
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "not implemented" in exc.detail
