import uuid
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.policy import PolicySource
from app.services.policy_seed import seed_policy_library


def test_seed_policy_library_idempotent(db_session: Session):
    """Re-running the seed function does not create duplicate policy records."""
    count_first = seed_policy_library(db_session)
    count_second = seed_policy_library(db_session)
    assert count_second == 0  # Idempotent


def test_list_policies(client: TestClient):
    """GET /api/policies lists policy sources without full document text."""
    response = client.get("/api/policies")
    assert response.status_code == status.HTTP_200_OK
    policies = response.json()
    assert len(policies) >= 4
    for p in policies:
        assert "id" in p
        assert "title" in p
        assert "source_type" in p
        assert "document_text" not in p  # Omitted in summary listing


def test_get_policy_detail(client: TestClient):
    """GET /api/policies/{policy_id} returns complete document details."""
    response = client.get("/api/policies/policy_demo_mfg_repair_01")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == "policy_demo_mfg_repair_01"
    assert "DEMO POLICY" in data["title"]
    assert "Section 1: Repair Attempt Limitations" in data["document_text"]


def test_consumer_helpline_seed_is_only_a_reference_pointer(client: TestClient):
    response = client.get("/api/policies/policy_official_consumer_guidance_in_03")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["source_type"] == "GUIDANCE"
    assert "REFERENCE POINTER" in data["title"]
    assert "does not contain a verified excerpt" in data["document_text"]
    assert "entitled to seek redressal" not in data["document_text"]


def test_get_policy_unknown_id_returns_404(client: TestClient):
    """GET /api/policies/{policy_id} returns 404 for unknown ID."""
    response = client.get("/api/policies/unknown_policy_id_999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_search_policies_matching_query(client: TestClient):
    """POST /api/policies/search returns matching passages with citations and scores."""
    payload = {
        "query": "laptop repair attempts defective replacement refund",
        "product_category": "laptop",
        "limit": 3,
    }
    response = client.post("/api/policies/search", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_results"] > 0
    top_result = data["results"][0]
    assert top_result["source_id"].startswith("policy_")
    assert len(top_result["passage"]) > 20
    assert top_result["relevance_score"] > 0


def test_search_policies_irrelevant_query(client: TestClient):
    """POST /api/policies/search returns empty list for completely irrelevant query."""
    payload = {
        "query": "astronomy telescopes galactic nebula quasar",
        "limit": 3,
    }
    response = client.post("/api/policies/search", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_results"] == 0
    assert data["results"] == []


def test_search_policies_validates_empty_query(client: TestClient):
    """POST /api/policies/search rejects empty query."""
    response = client.post("/api/policies/search", json={"query": ""})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
