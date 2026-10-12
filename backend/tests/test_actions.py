import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import status
from fastapi.testclient import TestClient


def test_action_creation_and_persistence(client: TestClient):
    """POST /api/cases/{case_id}/actions creates a proposed action with PENDING_APPROVAL status."""
    # 1. Create a case
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Action Test Case",
            "product_name": "Dell XPS 15",
            "issue_description": "Motherboard failed twice.",
        },
    )
    case_id = case_resp.json()["id"]

    # 2. Propose SEND_MESSAGE action
    action_payload = {
        "action_type": "SEND_MESSAGE",
        "title": "Escalation to Manufacturer Support",
        "description": "Request replacement authorization under two-repair failure guidelines.",
        "payload": {
            "recipient": "support-escalations@example.com",
            "subject": "Formal Replacement Request - Case Reference",
            "message_body": "Unit has undergone two unsuccessful repairs for the identical defect.",
            "is_simulated": True,
        },
    }
    response = client.post(f"/api/cases/{case_id}/actions", json=action_payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["case_id"] == case_id
    assert data["action_type"] == "SEND_MESSAGE"
    assert data["status"] == "PENDING_APPROVAL"
    assert data["approved_at"] is None
    assert data["executed_at"] is None

    # Verify timeline event was recorded
    timeline = client.get(f"/api/cases/{case_id}/timeline").json()
    assert any(e["event_type"] == "ACTION_CREATED" for e in timeline)


def test_action_retrieval(client: TestClient):
    """GET /api/cases/{case_id}/actions and GET /api/actions/{action_id}."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Action Retrieval", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = case_resp.json()["id"]

    create_resp = client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "action_type": "SCHEDULE_FOLLOW_UP",
            "title": "Follow up on repair status",
            "description": "Check if technician responded",
            "payload": {
                "due_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                "purpose": "Verify repair progress",
            },
        },
    )
    action_id = create_resp.json()["id"]

    # List actions for case
    list_resp = client.get(f"/api/cases/{case_id}/actions")
    assert list_resp.status_code == status.HTTP_200_OK
    assert len(list_resp.json()) == 1

    # Get single action
    get_resp = client.get(f"/api/actions/{action_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == action_id


def test_edit_action_reverts_approval(client: TestClient):
    """Editing an action invalidates previous approval and returns status to PENDING_APPROVAL."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Edit Action Case", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = case_resp.json()["id"]

    create_resp = client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "action_type": "SEND_MESSAGE",
            "title": "Initial Message",
            "description": "Initial desc",
            "payload": {
                "recipient": "support@example.com",
                "message_body": "Initial body",
            },
        },
    )
    action_id = create_resp.json()["id"]

    # 1. Approve
    client.post(f"/api/actions/{action_id}/approve")
    check_app = client.get(f"/api/actions/{action_id}").json()
    assert check_app["status"] == "APPROVED"

    # 2. Edit
    patch_resp = client.patch(
        f"/api/actions/{action_id}",
        json={"title": "Edited Message Title"},
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    updated = patch_resp.json()
    assert updated["title"] == "Edited Message Title"
    # Prior approval must be invalidated!
    assert updated["status"] == "PENDING_APPROVAL"
    assert updated["approved_at"] is None

    # Timeline event
    timeline = client.get(f"/api/cases/{case_id}/timeline").json()
    assert any(e["event_type"] == "ACTION_UPDATED" for e in timeline)


def test_execution_blocked_without_approval(client: TestClient):
    """POST /api/actions/{action_id}/execute returns 409 if status is not APPROVED."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Unapproved Exec", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = case_resp.json()["id"]

    create_resp = client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "action_type": "SEND_MESSAGE",
            "title": "Draft message",
            "description": "Desc",
            "payload": {"recipient": "test@test.com", "message_body": "Body"},
        },
    )
    action_id = create_resp.json()["id"]

    # Try executing without approval
    exec_resp = client.post(f"/api/actions/{action_id}/execute")
    assert exec_resp.status_code == status.HTTP_409_CONFLICT
    assert "blocked" in exec_resp.json()["detail"].lower()


def test_rejection_blocks_execution(client: TestClient):
    """POST /api/actions/{action_id}/reject sets REJECTED status and blocks execution."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Reject Action", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = case_resp.json()["id"]

    create_resp = client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "action_type": "SEND_MESSAGE",
            "title": "Rejected message",
            "description": "Desc",
            "payload": {"recipient": "test@test.com", "message_body": "Body"},
        },
    )
    action_id = create_resp.json()["id"]

    # Reject
    rej_resp = client.post(f"/api/actions/{action_id}/reject")
    assert rej_resp.status_code == status.HTTP_200_OK
    assert rej_resp.json()["status"] == "REJECTED"

    # Execution attempt must be rejected
    exec_resp = client.post(f"/api/actions/{action_id}/execute")
    assert exec_resp.status_code == status.HTTP_409_CONFLICT


def test_simulated_execution_and_idempotency(client: TestClient):
    """Approved action executes in simulated environment; repeated execution is idempotent."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Exec Test", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = case_resp.json()["id"]

    create_resp = client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "action_type": "SEND_MESSAGE",
            "title": "Send formal notice",
            "description": "Desc",
            "payload": {
                "recipient": "manufacturer@example.com",
                "subject": "Formal Grievance",
                "message_body": "Defect recurred twice.",
            },
        },
    )
    action_id = create_resp.json()["id"]

    # 1. Approve
    client.post(f"/api/actions/{action_id}/approve")

    # 2. Execute
    exec_resp = client.post(f"/api/actions/{action_id}/execute")
    assert exec_resp.status_code == status.HTTP_200_OK
    exec_data = exec_resp.json()
    assert exec_data["status"] == "EXECUTED"
    assert exec_data["is_simulated"] is True
    assert exec_data["execution_result"]["simulated"] is True

    # 3. Repeated execution call (Idempotency)
    repeat_resp = client.post(f"/api/actions/{action_id}/execute")
    assert repeat_resp.status_code == status.HTTP_200_OK
    assert "already executed" in repeat_resp.json()["message"].lower()

    # Timeline event check
    timeline = client.get(f"/api/cases/{case_id}/timeline").json()
    assert any(e["event_type"] == "ACTION_EXECUTED" for e in timeline)


def test_follow_up_scheduling_and_overdue_calculation(client: TestClient):
    """GET /api/cases/{case_id}/follow-ups correctly calculates overdue status."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Follow Up Case", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = case_resp.json()["id"]

    past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    # 1. Overdue follow-up
    client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "action_type": "SCHEDULE_FOLLOW_UP",
            "title": "Past check",
            "description": "Check past reply",
            "payload": {"due_at": past_time, "purpose": "Overdue purpose"},
        },
    )

    # 2. Future follow-up
    client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "action_type": "SCHEDULE_FOLLOW_UP",
            "title": "Future check",
            "description": "Check future reply",
            "payload": {"due_at": future_time, "purpose": "Upcoming purpose"},
        },
    )

    fu_resp = client.get(f"/api/cases/{case_id}/follow-ups")
    assert fu_resp.status_code == status.HTTP_200_OK
    follow_ups = fu_resp.json()
    assert len(follow_ups) == 2

    # Map by title
    fu_map = {f["title"]: f for f in follow_ups}
    assert fu_map["Past check"]["is_overdue"] is True
    assert fu_map["Future check"]["is_overdue"] is False
