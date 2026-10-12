import uuid
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.case import Case, CaseStatus


def test_list_cases_empty(client: TestClient):
    """GET /api/cases returns an empty list when no cases exist."""
    response = client.get("/api/cases")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_create_case_valid(client: TestClient, db_session: Session):
    """POST /api/cases creates a case with unique ID, default status, and timestamps."""
    payload = {
        "title": "Repeated laptop repair failure",
        "product_name": "Dell XPS 15",
        "issue_description": "Motherboard replaced twice; screen flickering returns within 48 hours.",
    }
    response = client.post("/api/cases", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Validate returned fields
    assert "id" in data
    assert uuid.UUID(data["id"])  # Valid UUID format
    assert data["title"] == payload["title"]
    assert data["product_name"] == payload["product_name"]
    assert data["issue_description"] == payload["issue_description"]
    assert data["status"] == "NEW"
    assert "created_at" in data
    assert "updated_at" in data

    # Verify actual persistence in SQLite
    persisted = db_session.query(Case).filter(Case.id == data["id"]).first()
    assert persisted is not None
    assert persisted.title == payload["title"]
    assert persisted.status == CaseStatus.NEW


def test_list_cases_returns_persisted_records(client: TestClient):
    """GET /api/cases retrieves created cases in descending order."""
    case1 = {
        "title": "Case 1",
        "product_name": "Product 1",
        "issue_description": "First issue description.",
    }
    case2 = {
        "title": "Case 2",
        "product_name": "Product 2",
        "issue_description": "Second issue description.",
    }

    client.post("/api/cases", json=case1)
    client.post("/api/cases", json=case2)

    response = client.get("/api/cases")
    assert response.status_code == status.HTTP_200_OK
    cases = response.json()
    assert len(cases) == 2
    titles = [c["title"] for c in cases]
    assert "Case 1" in titles
    assert "Case 2" in titles


def test_get_case_by_id_success(client: TestClient):
    """GET /api/cases/{case_id} returns the correct record when it exists."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Battery draining defect",
            "product_name": "MacBook Pro",
            "issue_description": "Battery drains 50% in 1 hour after third service center visit.",
        },
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    created_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/cases/{created_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    data = get_resp.json()
    assert data["id"] == created_id
    assert data["product_name"] == "MacBook Pro"
    assert data["status"] == "NEW"


def test_get_case_by_id_not_found(client: TestClient):
    """GET /api/cases/{case_id} returns HTTP 404 for non-existent ID."""
    unknown_id = str(uuid.uuid4())
    response = client.get(f"/api/cases/{unknown_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_create_case_rejects_empty_title(client: TestClient):
    """Validation: Reject empty or whitespace-only title."""
    payload = {
        "title": "   ",
        "product_name": "Laptop",
        "issue_description": "Fault description.",
    }
    response = client.post("/api/cases", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_case_rejects_empty_product_name(client: TestClient):
    """Validation: Reject empty or whitespace-only product_name."""
    payload = {
        "title": "Repair Issue",
        "product_name": "  ",
        "issue_description": "Fault description.",
    }
    response = client.post("/api/cases", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_case_rejects_empty_issue_description(client: TestClient):
    """Validation: Reject empty or whitespace-only issue_description."""
    payload = {
        "title": "Repair Issue",
        "product_name": "Laptop",
        "issue_description": "",
    }
    response = client.post("/api/cases", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_case_rejects_missing_fields(client: TestClient):
    """Validation: Reject payload missing required fields."""
    response = client.post("/api/cases", json={"title": "Missing fields"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_case_status_enum_values():
    """Verify supported statuses match specification."""
    expected = {
        "NEW",
        "COLLECTING_EVIDENCE",
        "UNDER_REVIEW",
        "ACTION_READY",
        "AWAITING_RESPONSE",
        "FOLLOW_UP_DUE",
        "RESOLVED",
        "CLOSED",
    }
    actual = {s.value for s in CaseStatus}
    assert actual == expected
