import uuid
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.case import Case
from app.models.event import CaseEvent, EventType, EventSource


def test_timeline_case_creation_event(client: TestClient):
    """Creating a case automatically creates a CASE_CREATED event."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Timeline Test Case",
            "product_name": "Test Laptop",
            "issue_description": "Initial issue for timeline test.",
        },
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    case_id = create_resp.json()["id"]

    resp = client.get(f"/api/cases/{case_id}/timeline")
    assert resp.status_code == status.HTTP_200_OK
    events = resp.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "CASE_CREATED"
    assert events[0]["source_type"] == "SYSTEM"
    assert "Test Laptop" in events[0]["description"]
    assert events[0]["metadata_json"]["initial_status"] == "NEW"


def test_timeline_case_updated_event(client: TestClient):
    """Updating a case creates a CASE_UPDATED event with changed fields in metadata."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Old Title",
            "product_name": "Old Product",
            "issue_description": "Old Description",
        },
    )
    case_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/cases/{case_id}",
        json={"title": "New Title", "issue_description": "New Description"},
    )
    assert patch_resp.status_code == status.HTTP_200_OK

    t_resp = client.get(f"/api/cases/{case_id}/timeline")
    assert t_resp.status_code == status.HTTP_200_OK
    events = t_resp.json()
    assert len(events) == 2
    update_event = events[1]
    assert update_event["event_type"] == "CASE_UPDATED"
    assert "title" in update_event["metadata_json"]["changed_fields"]
    assert "issue_description" in update_event["metadata_json"]["changed_fields"]
    assert update_event["metadata_json"]["old_values"]["title"] == "Old Title"
    assert update_event["metadata_json"]["new_values"]["title"] == "New Title"


def test_timeline_status_changed_event(client: TestClient):
    """Changing case status records a STATUS_CHANGED event with previous and new status."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Status Event Case",
            "product_name": "Laptop",
            "issue_description": "Issue",
        },
    )
    case_id = create_resp.json()["id"]

    client.patch(f"/api/cases/{case_id}/status", json={"status": "UNDER_REVIEW"})

    t_resp = client.get(f"/api/cases/{case_id}/timeline")
    assert t_resp.status_code == status.HTTP_200_OK
    events = t_resp.json()
    assert len(events) == 2
    status_event = events[1]
    assert status_event["event_type"] == "STATUS_CHANGED"
    assert status_event["metadata_json"]["previous_status"] == "NEW"
    assert status_event["metadata_json"]["new_status"] == "UNDER_REVIEW"


def test_add_user_note_success(client: TestClient):
    """POST /api/cases/{case_id}/events adds a NOTE_ADDED event with USER source."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Note Test Case",
            "product_name": "Laptop",
            "issue_description": "Issue",
        },
    )
    case_id = create_resp.json()["id"]

    note_payload = {
        "event_type": "NOTE_ADDED",
        "description": "Technician stated part is out of stock.",
    }
    resp = client.post(f"/api/cases/{case_id}/events", json=note_payload)
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["event_type"] == "NOTE_ADDED"
    assert data["source_type"] == "USER"
    assert data["description"] == note_payload["description"]


def test_add_user_note_rejects_empty_description(client: TestClient):
    """POST /api/cases/{case_id}/events rejects whitespace or empty description."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Note Test Case",
            "product_name": "Laptop",
            "issue_description": "Issue",
        },
    )
    case_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/cases/{case_id}/events",
        json={"event_type": "NOTE_ADDED", "description": "   "},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_add_user_note_rejects_disallowed_event_type(client: TestClient):
    """POST /api/cases/{case_id}/events rejects event_type other than NOTE_ADDED."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Note Test Case",
            "product_name": "Laptop",
            "issue_description": "Issue",
        },
    )
    case_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/cases/{case_id}/events",
        json={"event_type": "SYSTEM_EVENT", "description": "Arbitrary event"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_timeline_chronological_ordering_and_pagination(client: TestClient):
    """GET /api/cases/{case_id}/timeline returns events in chronological order with pagination."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Ordering Test Case",
            "product_name": "Laptop",
            "issue_description": "Issue",
        },
    )
    case_id = create_resp.json()["id"]

    # 1. Add note A
    client.post(
        f"/api/cases/{case_id}/events",
        json={"event_type": "NOTE_ADDED", "description": "Note 1"},
    )
    # 2. Update case
    client.patch(f"/api/cases/{case_id}", json={"title": "Ordering Case Updated"})
    # 3. Status change
    client.patch(f"/api/cases/{case_id}/status", json={"status": "UNDER_REVIEW"})
    # 4. Add note B
    client.post(
        f"/api/cases/{case_id}/events",
        json={"event_type": "NOTE_ADDED", "description": "Note 2"},
    )

    # Total events: 5 (CASE_CREATED, NOTE_ADDED, CASE_UPDATED, STATUS_CHANGED, NOTE_ADDED)
    full_resp = client.get(f"/api/cases/{case_id}/timeline")
    assert full_resp.status_code == status.HTTP_200_OK
    events = full_resp.json()
    assert len(events) == 5
    types = [e["event_type"] for e in events]
    assert types == [
        "CASE_CREATED",
        "NOTE_ADDED",
        "CASE_UPDATED",
        "STATUS_CHANGED",
        "NOTE_ADDED",
    ]

    # Test pagination: limit=2, skip=1
    paginated_resp = client.get(f"/api/cases/{case_id}/timeline?skip=1&limit=2")
    assert paginated_resp.status_code == status.HTTP_200_OK
    p_events = paginated_resp.json()
    assert len(p_events) == 2
    assert p_events[0]["event_type"] == "NOTE_ADDED"
    assert p_events[0]["description"] == "Note 1"
    assert p_events[1]["event_type"] == "CASE_UPDATED"


def test_timeline_unknown_case_returns_404(client: TestClient):
    """GET /api/cases/{case_id}/timeline returns 404 for unknown case ID."""
    unknown_id = str(uuid.uuid4())
    resp = client.get(f"/api/cases/{unknown_id}/timeline")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_add_event_unknown_case_returns_404(client: TestClient):
    """POST /api/cases/{case_id}/events returns 404 for unknown case ID."""
    unknown_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/cases/{unknown_id}/events",
        json={"event_type": "NOTE_ADDED", "description": "Note for non-existent case"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND
