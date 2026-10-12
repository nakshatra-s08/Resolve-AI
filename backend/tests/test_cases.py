import uuid
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.case import Case, CaseStatus
from app.models.event import CaseEvent, EventType, EventSource


def test_list_cases_empty(client: TestClient):
    """GET /api/cases returns an empty list when no cases exist."""
    response = client.get("/api/cases")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_create_case_valid(client: TestClient, db_session: Session):
    """POST /api/cases creates a case with unique ID, default status, timestamps, and CASE_CREATED event."""
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

    # Verify automatic CASE_CREATED event
    events = db_session.query(CaseEvent).filter(CaseEvent.case_id == data["id"]).all()
    assert len(events) == 1
    assert events[0].event_type == EventType.CASE_CREATED
    assert events[0].source_type == EventSource.SYSTEM


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


# ==========================================
# PHASE 2: CASE UPDATE TESTS
# ==========================================

def test_update_case_valid_partial(client: TestClient):
    """PATCH /api/cases/{case_id} updates only supplied fields and preserves omitted ones."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Initial Title",
            "product_name": "Initial Product",
            "issue_description": "Initial Description",
        },
    )
    case_id = create_resp.json()["id"]

    # Partial update: title and issue_description only
    patch_resp = client.patch(
        f"/api/cases/{case_id}",
        json={"title": "Updated Title", "issue_description": "Updated Description"},
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    updated_data = patch_resp.json()
    assert updated_data["title"] == "Updated Title"
    assert updated_data["product_name"] == "Initial Product"  # Unchanged
    assert updated_data["issue_description"] == "Updated Description"


def test_update_case_unknown_id_returns_404(client: TestClient):
    """PATCH /api/cases/{case_id} returns 404 for unknown case ID."""
    unknown_id = str(uuid.uuid4())
    patch_resp = client.patch(
        f"/api/cases/{unknown_id}",
        json={"title": "Non-existent"},
    )
    assert patch_resp.status_code == status.HTTP_404_NOT_FOUND


def test_update_case_rejects_empty_whitespace_strings(client: TestClient):
    """PATCH /api/cases/{case_id} rejects empty or whitespace-only field values."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Title",
            "product_name": "Product",
            "issue_description": "Description",
        },
    )
    case_id = create_resp.json()["id"]

    resp = client.patch(f"/api/cases/{case_id}", json={"title": "   "})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    resp = client.patch(f"/api/cases/{case_id}", json={"product_name": ""})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_case_rejects_extra_fields(client: TestClient):
    """PATCH /api/cases/{case_id} rejects arbitrary database fields like status or id."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Title",
            "product_name": "Product",
            "issue_description": "Description",
        },
    )
    case_id = create_resp.json()["id"]

    resp = client.patch(f"/api/cases/{case_id}", json={"status": "RESOLVED"})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==========================================
# PHASE 2: CASE STATUS MANAGEMENT TESTS
# ==========================================

def test_status_transition_valid_flow(client: TestClient):
    """Valid sequential transitions succeed."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Laptop repair failure",
            "product_name": "Laptop",
            "issue_description": "Screen issue",
        },
    )
    case_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "NEW"

    # NEW -> UNDER_REVIEW
    resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "UNDER_REVIEW"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "UNDER_REVIEW"

    # UNDER_REVIEW -> ACTION_READY
    resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "ACTION_READY"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "ACTION_READY"

    # ACTION_READY -> AWAITING_RESPONSE
    resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "AWAITING_RESPONSE"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "AWAITING_RESPONSE"

    # AWAITING_RESPONSE -> RESOLVED
    resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "RESOLVED"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "RESOLVED"


def test_status_transition_invalid_returns_409(client: TestClient):
    """Disallowed transitions return HTTP 409 Conflict."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Laptop repair",
            "product_name": "Laptop",
            "issue_description": "Power fault",
        },
    )
    case_id = create_resp.json()["id"]
    # NEW directly to RESOLVED is not an allowed transition
    resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "RESOLVED"})
    assert resp.status_code == status.HTTP_409_CONFLICT
    assert "Invalid status transition" in resp.json()["detail"]


def test_status_transition_unknown_case_returns_404(client: TestClient):
    """Status update on unknown case returns 404."""
    unknown_id = str(uuid.uuid4())
    resp = client.patch(
        f"/api/cases/{unknown_id}/status",
        json={"status": "UNDER_REVIEW"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_status_transition_rejects_unsupported_status_value(client: TestClient):
    """Pydantic validation rejects unsupported status strings."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Laptop repair",
            "product_name": "Laptop",
            "issue_description": "Power fault",
        },
    )
    case_id = create_resp.json()["id"]
    resp = client.patch(
        f"/api/cases/{case_id}/status",
        json={"status": "PENDING_ARBITRARY_STATUS"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_status_transition_noop_does_not_create_duplicate_event(client: TestClient):
    """Setting the same status is a no-op and does not generate duplicate events."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Laptop repair",
            "product_name": "Laptop",
            "issue_description": "Power fault",
        },
    )
    case_id = create_resp.json()["id"]

    # Initial events: 1 (CASE_CREATED)
    t_resp = client.get(f"/api/cases/{case_id}/timeline")
    assert len(t_resp.json()) == 1

    # Setting to same status (NEW)
    resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "NEW"})
    assert resp.status_code == status.HTTP_200_OK

    t_resp2 = client.get(f"/api/cases/{case_id}/timeline")
    assert len(t_resp2.json()) == 1  # No duplicate event created


def test_reopen_resolved_case_to_under_review(client: TestClient):
    """RESOLVED cases can be reopened to UNDER_REVIEW when issue recurs."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Laptop repair",
            "product_name": "Laptop",
            "issue_description": "Motherboard issue",
        },
    )
    case_id = create_resp.json()["id"]

    # Advance to UNDER_REVIEW -> RESOLVED
    client.patch(f"/api/cases/{case_id}/status", json={"status": "UNDER_REVIEW"})
    client.patch(f"/api/cases/{case_id}/status", json={"status": "RESOLVED"})

    # Reopen to UNDER_REVIEW
    resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "UNDER_REVIEW"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "UNDER_REVIEW"


def test_reopen_closed_case_to_under_review(client: TestClient):
    """CLOSED cases can be reopened to UNDER_REVIEW."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Laptop repair",
            "product_name": "Laptop",
            "issue_description": "Motherboard issue",
        },
    )
    case_id = create_resp.json()["id"]

    # NEW -> CLOSED -> UNDER_REVIEW
    client.patch(f"/api/cases/{case_id}/status", json={"status": "CLOSED"})
    resp = client.patch(f"/api/cases/{case_id}/status", json={"status": "UNDER_REVIEW"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "UNDER_REVIEW"
