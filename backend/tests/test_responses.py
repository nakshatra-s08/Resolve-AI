import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from tests.test_evidence import create_minimal_pdf


def test_simulated_response_creation_and_timeline(client: TestClient):
    """POST /api/cases/{case_id}/simulate-response persists response and creates timeline event."""
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Provider Response Test",
            "product_name": "Dell XPS 15",
            "issue_description": "Motherboard failed twice.",
        },
    )
    case_id = case_resp.json()["id"]

    # Ingest simulated provider response
    resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "We acknowledge your repair complaint. Please provide the job sheet from the second service visit.",
            "provider_name": "Acme Repair Services",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["provider_name"] == "Acme Repair Services"
    assert data["source_type"] == "SIMULATION"
    assert data["is_simulated"] is True
    assert data["status"] == "RECEIVED"

    # Verify timeline event was added
    timeline = client.get(f"/api/cases/{case_id}/timeline").json()
    assert any(e["event_type"] == "SIMULATED_RESPONSE_RECEIVED" for e in timeline)
    assert any(e["source_type"] == "SIMULATION" for e in timeline)


def test_simulated_response_validates_cross_case_action(client: TestClient):
    """Reject simulated response if related_action_id belongs to a different case."""
    # Case A
    case_a = client.post(
        "/api/cases",
        json={"title": "Case A", "product_name": "Laptop A", "issue_description": "Issue"},
    ).json()
    # Case B
    case_b = client.post(
        "/api/cases",
        json={"title": "Case B", "product_name": "Laptop B", "issue_description": "Issue"},
    ).json()

    # Create action in Case A
    act_a = client.post(
        f"/api/cases/{case_a['id']}/actions",
        json={
            "action_type": "SEND_MESSAGE",
            "title": "Message A",
            "description": "Desc",
            "payload": {"recipient": "vendor@test.com", "message_body": "Hello"},
        },
    ).json()

    # Attempt to associate Action A with Case B
    bad_resp = client.post(
        f"/api/cases/{case_b['id']}/simulate-response",
        json={
            "response_text": "Response referencing wrong action",
            "related_action_id": act_a["id"],
        },
    )
    assert bad_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "belongs to a different case" in bad_resp.json()["detail"].lower()


def test_simulated_response_completes_related_follow_up(client: TestClient):
    """A response referencing a SCHEDULE_FOLLOW_UP action completes/executes that follow-up."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Followup Case", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = case_resp.json()["id"]

    # Schedule follow-up
    fu_resp = client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "action_type": "SCHEDULE_FOLLOW_UP",
            "title": "Await vendor reply",
            "description": "Waiting for vendor reply",
            "payload": {
                "due_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                "purpose": "Vendor status check",
            },
        },
    )
    act_id = fu_resp.json()["id"]

    # Receive response referencing action
    client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Here is our formal update.",
            "related_action_id": act_id,
        },
    )

    # Check action status
    act_check = client.get(f"/api/actions/{act_id}").json()
    assert act_check["status"] == "EXECUTED"
    assert act_check["execution_result_json"]["completed_by_response_id"] is not None


def test_process_response_identifies_missing_and_available_evidence(client: TestClient):
    """POST /api/cases/{case_id}/responses/{response_id}/process analyzes document requests vs attached evidence."""
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Analysis Case",
            "product_name": "MacBook Pro",
            "issue_description": "Logic board replaced twice.",
        },
    )
    case_id = case_resp.json()["id"]

    # Upload INVOICE only
    inv_pdf = create_minimal_pdf("Apple Invoice 99999")
    client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("invoice.pdf", inv_pdf, "application/pdf")},
        data={"evidence_type": "INVOICE"},
    )

    # Ingest provider response requesting BOTH invoice and repair job sheet
    resp_create = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Before we evaluate replacement, please provide your original invoice and the repair receipt / job sheet.",
            "provider_name": "Apple Authorized Service",
        },
    )
    resp_id = resp_create.json()["id"]

    # Process response
    proc_resp = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    assert proc_resp.status_code == status.HTTP_200_OK
    proc_data = proc_resp.json()

    assert proc_data["case_id"] == case_id
    assert proc_data["response_id"] == resp_id
    assert proc_data["engine_mode"] == "demo"

    # Invoice should be flagged as ALREADY AVAILABLE
    assert len(proc_data["evidence_already_available"]) > 0
    assert any("invoice" in e.lower() for e in proc_data["evidence_already_available"])

    # Repair receipt should be flagged as STILL NEEDED
    assert len(proc_data["evidence_still_needed"]) > 0
    assert any("repair" in e.lower() for e in proc_data["evidence_still_needed"])

    # Case status should transition to COLLECTING_EVIDENCE
    case_check = client.get(f"/api/cases/{case_id}").json()
    assert case_check["status"] == "COLLECTING_EVIDENCE"


def test_process_response_idempotency(client: TestClient):
    """Reprocessing the same response is idempotent and does not create duplicate events."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Idempotent Case", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = case_resp.json()["id"]

    resp_create = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={"response_text": "We cannot guarantee replacement as per policy."},
    )
    resp_id = resp_create.json()["id"]

    # First process
    p1 = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    assert p1.status_code == status.HTTP_200_OK

    t1 = client.get(f"/api/cases/{case_id}/timeline").json()
    events_count_1 = len(t1)

    # Second process (idempotent call)
    p2 = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    assert p2.status_code == status.HTTP_200_OK
    assert p2.json()["summary"] == p1.json()["summary"]

    t2 = client.get(f"/api/cases/{case_id}/timeline").json()
    assert len(t2) == events_count_1  # No duplicate timeline events!


def test_case_reassessment_after_simulated_response(client: TestClient):
    """After a response is processed, GET/POST analysis incorporates the new response context."""
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Reassessment Case",
            "product_name": "Lenovo Yoga",
            "issue_description": "Screen flickering after second service repair.",
        },
    )
    case_id = case_resp.json()["id"]

    # Ingest and process response
    resp_create = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={"response_text": "Service technician noted motherboard replacement failed again."},
    )
    resp_id = resp_create.json()["id"]
    client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")

    # Re-analyze case
    reanalysis = client.post(f"/api/cases/{case_id}/analysis")
    assert reanalysis.status_code == status.HTTP_200_OK
    data = reanalysis.json()
    assert data["case_id"] == case_id
    assert len(data["supporting_policy_sources"]) > 0
