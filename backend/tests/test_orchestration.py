import pytest
from fastapi import status
from fastapi.testclient import TestClient
from tests.test_evidence import create_minimal_pdf


def test_response_requests_missing_evidence(client: TestClient):
    """
    When a provider response requests documents not yet in evidence,
    the orchestrator sets wait_state to WAITING_FOR_USER_INPUT,
    stage to EVIDENCE_GATHERING, records pending evidence, and proposes NO action.
    """
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Missing Evidence Test",
            "product_name": "Asus ZenBook",
            "issue_description": "Keyboard backlight failed twice.",
        },
    )
    assert case_resp.status_code == status.HTTP_201_CREATED
    case_id = case_resp.json()["id"]

    # Ingest provider response asking for invoice and repair receipt
    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Before evaluating warranty replacement, please provide your original purchase invoice and job sheet / repair receipt.",
            "provider_name": "Asus Service Hub",
        },
    )
    assert sim_resp.status_code == status.HTTP_201_CREATED
    resp_id = sim_resp.json()["id"]

    # Process response
    proc_resp = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    assert proc_resp.status_code == status.HTTP_200_OK
    data = proc_resp.json()

    # Verify workflow state in response
    wf = data["workflow_state"]
    assert wf is not None
    assert wf["stage"] == "EVIDENCE_GATHERING"
    assert wf["wait_state"] == "WAITING_FOR_USER_INPUT"
    assert len(wf["pending_evidence"]) > 0
    assert any("invoice" in e.lower() or "repair" in e.lower() for e in wf["pending_evidence"])
    assert wf["active_action_id"] is None
    assert data["proposed_action"] is None

    # Verify case status
    case_check = client.get(f"/api/cases/{case_id}").json()
    assert case_check["status"] == "COLLECTING_EVIDENCE"

    # Verify no action records were created
    actions = client.get(f"/api/cases/{case_id}/actions").json()
    assert len(actions) == 0

    # Verify timeline records WORKFLOW_REASSESSED event
    timeline = client.get(f"/api/cases/{case_id}/timeline").json()
    assert any(e["event_type"] == "WORKFLOW_REASSESSED" for e in timeline)


def test_response_justifies_proposing_concrete_action(client: TestClient):
    """
    When a provider response offers commitments/resolution without missing evidence,
    the orchestrator creates at most one PENDING_APPROVAL action and sets
    wait_state to WAITING_FOR_ACTION_APPROVAL.
    """
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Action Proposal Test",
            "product_name": "Dell XPS 13",
            "issue_description": "Motherboard failed twice.",
        },
    )
    case_id = case_resp.json()["id"]

    # Ingest provider response offering replacement
    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "We acknowledge the repeated hardware failure. We have approved and agreed to replace your device with a new unit.",
            "provider_name": "Dell Official Support",
        },
    )
    resp_id = sim_resp.json()["id"]

    # Process response
    proc_resp = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    assert proc_resp.status_code == status.HTTP_200_OK
    data = proc_resp.json()

    # Verify workflow state
    wf = data["workflow_state"]
    assert wf is not None
    assert wf["stage"] == "ACTION_PENDING"
    assert wf["wait_state"] == "WAITING_FOR_ACTION_APPROVAL"
    assert wf["active_action_id"] is not None

    # Verify action proposal returned and persisted
    proposed_act = data["proposed_action"]
    assert proposed_act is not None
    assert proposed_act["id"] == wf["active_action_id"]
    assert proposed_act["status"] == "PENDING_APPROVAL"
    assert proposed_act["payload_json"]["is_simulated"] is True

    # Verify in actions endpoint
    actions = client.get(f"/api/cases/{case_id}/actions").json()
    assert len(actions) == 1
    assert actions[0]["id"] == proposed_act["id"]
    assert actions[0]["status"] == "PENDING_APPROVAL"


def test_response_requires_waiting_for_external_reply(client: TestClient):
    """
    When a provider response indicates the matter is forwarded for internal investigation
    without requesting user evidence or offering resolution,
    the orchestrator transitions wait_state to WAITING_FOR_EXTERNAL_RESPONSE and stage to AWAITING_RESPONSE.
    """
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "External Wait Test",
            "product_name": "HP Spectre",
            "issue_description": "Screen lines after repair.",
        },
    )
    case_id = case_resp.json()["id"]

    # Provider notes investigation in progress
    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Your claim has been forwarded to our engineering team for technical review. Investigation in progress, please allow 3-5 business days for our formal update.",
            "provider_name": "HP Technical Center",
        },
    )
    resp_id = sim_resp.json()["id"]

    # Process response
    proc_resp = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    assert proc_resp.status_code == status.HTTP_200_OK
    data = proc_resp.json()

    wf = data["workflow_state"]
    assert wf is not None
    assert wf["stage"] == "AWAITING_RESPONSE"
    assert wf["wait_state"] == "WAITING_FOR_EXTERNAL_RESPONSE"
    assert len(wf["pending_evidence"]) == 0
    assert wf["active_action_id"] is None

    # Verify case status transitioned
    case_check = client.get(f"/api/cases/{case_id}").json()
    assert case_check["status"] == "AWAITING_RESPONSE"


def test_repeated_processing_does_not_create_duplicate_actions(client: TestClient):
    """
    Reprocessing the same response is idempotent and never creates duplicate actions or events.
    """
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Idempotency Test",
            "product_name": "Lenovo ThinkPad",
            "issue_description": "TrackPoint malfunction.",
        },
    )
    case_id = case_resp.json()["id"]

    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Replacement authorized for the defective keyboard and TrackPoint assembly.",
            "provider_name": "Lenovo Support",
        },
    )
    resp_id = sim_resp.json()["id"]

    # First process call
    p1 = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    assert p1.status_code == status.HTTP_200_OK
    actions_1 = client.get(f"/api/cases/{case_id}/actions").json()
    timeline_1 = client.get(f"/api/cases/{case_id}/timeline").json()
    assert len(actions_1) == 1

    # Second process call (idempotent replay)
    p2 = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    assert p2.status_code == status.HTTP_200_OK
    actions_2 = client.get(f"/api/cases/{case_id}/actions").json()
    timeline_2 = client.get(f"/api/cases/{case_id}/timeline").json()

    # Assert exactly 1 action, exactly same timeline length
    assert len(actions_2) == 1
    assert actions_2[0]["id"] == actions_1[0]["id"]
    assert len(timeline_2) == len(timeline_1)


def test_workflow_state_persistence_across_requests(client: TestClient):
    """
    Workflow state is persisted in SQLite and can be retrieved across independent requests via
    GET /api/cases/{case_id}/workflow-state and inside GET /api/cases/{case_id}.
    """
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Persistence Test",
            "product_name": "MacBook Air",
            "issue_description": "Battery drain issue.",
        },
    )
    case_id = case_resp.json()["id"]

    # Dedicated workflow-state endpoint immediately after creation
    wf_init = client.get(f"/api/cases/{case_id}/workflow-state")
    assert wf_init.status_code == status.HTTP_200_OK
    init_data = wf_init.json()
    assert init_data["case_id"] == case_id
    assert init_data["stage"] == "INTAKE"
    assert "warranty" in init_data["goal"].lower()

    # Process simulated response
    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Please provide invoice and repair receipt for diagnostic evaluation.",
            "provider_name": "Apple Care",
        },
    )
    resp_id = sim_resp.json()["id"]
    client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")

    # Fetch workflow state in fresh request
    wf_fresh = client.get(f"/api/cases/{case_id}/workflow-state")
    assert wf_fresh.status_code == status.HTTP_200_OK
    fresh_data = wf_fresh.json()
    assert fresh_data["stage"] == "EVIDENCE_GATHERING"
    assert fresh_data["wait_state"] == "WAITING_FOR_USER_INPUT"
    assert len(fresh_data["pending_evidence"]) > 0

    # Also verify workflow_state is included in CaseRead
    case_read = client.get(f"/api/cases/{case_id}")
    assert case_read.status_code == status.HTTP_200_OK
    case_read_data = case_read.json()
    assert case_read_data["workflow_state"] is not None
    assert case_read_data["workflow_state"]["stage"] == "EVIDENCE_GATHERING"


def test_no_action_is_automatically_approved_or_executed(client: TestClient):
    """
    Ensures that every action proposed through the orchestration engine is created
    strictly in PENDING_APPROVAL status. No action is ever auto-approved or executed.
    """
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Safety Test",
            "product_name": "Surface Pro",
            "issue_description": "Flickering screen.",
        },
    )
    case_id = case_resp.json()["id"]

    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "We offer a refund will be issued upon return of unit.",
            "provider_name": "Microsoft Service",
        },
    )
    resp_id = sim_resp.json()["id"]
    client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")

    # Query all actions
    actions = client.get(f"/api/cases/{case_id}/actions").json()
    assert len(actions) >= 1
    for act in actions:
        assert act["status"] == "PENDING_APPROVAL"
        assert act["approved_at"] is None
        assert act["executed_at"] is None
        assert act["execution_result_json"] is None


def test_complete_agentic_workflow_end_to_end(client: TestClient):
    """
    Complete end-to-end multi-step workflow:
    1. Case created (stage=INTAKE).
    2. Simulated provider response requests missing invoice.
    3. Response processed -> stage=EVIDENCE_GATHERING, wait_state=WAITING_FOR_USER_INPUT.
    4. User uploads requested invoice PDF.
    5. Second simulated provider response offers replacement.
    6. Response processed -> stage=ACTION_PENDING, wait_state=WAITING_FOR_ACTION_APPROVAL, proposed action created.
    7. User explicitly approves action -> status=APPROVED.
    8. User executes action -> status=EXECUTED, simulated result recorded.
    """
    # 1. Create case
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "End-to-End Orchestration Case",
            "product_name": "ThinkPad Carbon",
            "issue_description": "Motherboard and display failed repeatedly.",
        },
    )
    assert case_resp.status_code == status.HTTP_201_CREATED
    case_id = case_resp.json()["id"]

    # Initial workflow state
    wf_1 = client.get(f"/api/cases/{case_id}/workflow-state").json()
    assert wf_1["stage"] == "INTAKE"

    # 2. Ingest response requesting invoice
    sim_1 = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Please provide proof of purchase / invoice before we can evaluate your repeat repair claim.",
            "provider_name": "Lenovo Regional Repair Service",
        },
    ).json()

    # 3. Process response 1
    proc_1 = client.post(f"/api/cases/{case_id}/responses/{sim_1['id']}/process").json()
    assert proc_1["workflow_state"]["stage"] == "EVIDENCE_GATHERING"
    assert proc_1["workflow_state"]["wait_state"] == "WAITING_FOR_USER_INPUT"
    assert len(proc_1["workflow_state"]["pending_evidence"]) > 0
    assert proc_1["proposed_action"] is None

    # 4. User uploads invoice evidence
    invoice_pdf = create_minimal_pdf("ThinkPad Purchase Invoice 2025")
    upload_resp = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("invoice.pdf", invoice_pdf, "application/pdf")},
        data={"evidence_type": "INVOICE"},
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED

    # 5. Ingest second response offering replacement
    sim_2 = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Thank you for the invoice. We have approved and agreed to replace the unit with a new replacement device under warranty.",
            "provider_name": "Lenovo Regional Repair Service",
        },
    ).json()

    # 6. Process response 2
    proc_2 = client.post(f"/api/cases/{case_id}/responses/{sim_2['id']}/process").json()
    assert proc_2["workflow_state"]["stage"] == "ACTION_PENDING"
    assert proc_2["workflow_state"]["wait_state"] == "WAITING_FOR_ACTION_APPROVAL"
    assert proc_2["proposed_action"] is not None

    action_id = proc_2["proposed_action"]["id"]
    assert proc_2["proposed_action"]["status"] == "PENDING_APPROVAL"

    # 7. User explicitly approves action
    appr_resp = client.post(f"/api/actions/{action_id}/approve")
    assert appr_resp.status_code == status.HTTP_200_OK
    assert appr_resp.json()["status"] == "APPROVED"

    # 8. User executes action
    exec_resp = client.post(f"/api/actions/{action_id}/execute")
    assert exec_resp.status_code == status.HTTP_200_OK
    exec_data = exec_resp.json()
    assert exec_data["status"] == "EXECUTED"
    assert exec_data["is_simulated"] is True
    assert exec_data["execution_result"]["simulated"] is True


def test_workflow_state_consistency_on_status_change_and_evidence_lifecycle(client: TestClient):
    """
    Phase 8C Regression Test:
    Verify that:
    1. Case status changes to COLLECTING_EVIDENCE synchronize workflow stage and wait state.
    2. Simulated provider document requests populate pending_evidence.
    3. Uploading matching evidence dynamically satisfies pending_evidence via auto-reassessment.
    4. Deleting evidence re-activates pending_evidence requirements via auto-reassessment.
    5. GET /api/cases/{case_id}/workflow-state auto-reconciles stale placeholder states on non-NEW cases.
    """
    # 1. Create a case
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Consistency Lifecycle Test Case",
            "product_name": "Sony Wireless Headphones",
            "issue_description": "Intermittent charging failure.",
        },
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    case_id = create_resp.json()["id"]

    # Verify initial state is INTAKE
    wf_init = client.get(f"/api/cases/{case_id}/workflow-state").json()
    assert wf_init["stage"] == "INTAKE"
    assert wf_init["wait_state"] == "NONE"
    assert wf_init["pending_evidence"] == []

    # 2. Transition case status to COLLECTING_EVIDENCE
    status_resp = client.patch(
        f"/api/cases/{case_id}/status",
        json={"status": "COLLECTING_EVIDENCE"},
    )
    assert status_resp.status_code == status.HTTP_200_OK

    # Verify workflow state updated consistently
    wf_after_status = client.get(f"/api/cases/{case_id}/workflow-state").json()
    assert wf_after_status["stage"] == "EVIDENCE_GATHERING"
    assert wf_after_status["wait_state"] == "WAITING_FOR_USER_INPUT"

    # 3. Ingest simulated response requesting proof of purchase / invoice
    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Please provide your original purchase invoice and proof of purchase to proceed with warranty assessment.",
            "provider_name": "Sony Support",
        },
    )
    assert sim_resp.status_code == status.HTTP_201_CREATED
    sim_id = sim_resp.json()["id"]

    # Process response
    proc_resp = client.post(f"/api/cases/{case_id}/responses/{sim_id}/process")
    assert proc_resp.status_code == status.HTTP_200_OK
    wf_proc = proc_resp.json()["workflow_state"]
    assert wf_proc["stage"] == "EVIDENCE_GATHERING"
    assert wf_proc["wait_state"] == "WAITING_FOR_USER_INPUT"
    assert len(wf_proc["pending_evidence"]) > 0
    assert any("invoice" in e.lower() for e in wf_proc["pending_evidence"])

    # 4. Upload matching INVOICE evidence
    pdf_content = create_minimal_pdf("Sony Headphone Tax Invoice 2025")
    upload_resp = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("sony_invoice.pdf", pdf_content, "application/pdf")},
        data={"evidence_type": "INVOICE"},
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED
    evidence_id = upload_resp.json()["id"]

    # Verify workflow state dynamically satisfied pending evidence
    wf_after_upload = client.get(f"/api/cases/{case_id}/workflow-state").json()
    assert wf_after_upload["stage"] == "EVIDENCE_GATHERING"
    assert wf_after_upload["wait_state"] == "WAITING_FOR_USER_INPUT"
    assert wf_after_upload["pending_evidence"] == []

    # 5. Delete the invoice evidence
    del_resp = client.delete(f"/api/cases/{case_id}/evidence/{evidence_id}")
    assert del_resp.status_code == status.HTTP_200_OK

    # Verify workflow state re-activated pending evidence
    wf_after_delete = client.get(f"/api/cases/{case_id}/workflow-state").json()
    assert len(wf_after_delete["pending_evidence"]) > 0
    assert any("invoice" in e.lower() for e in wf_after_delete["pending_evidence"])


def test_missing_optional_warranty_does_not_block_progression(client: TestClient):
    """
    Test 1: Missing optional warranty document does not block workflow progression
    when core proof of purchase (INVOICE) and repair history (REPAIR_RECEIPT) are present.
    """
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Warranty Non-Blocking Test",
            "product_name": "Asus ROG Laptop",
            "issue_description": "Motherboard replaced twice; still crashing.",
        },
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    case_id = create_resp.json()["id"]

    # Upload INVOICE
    inv_pdf = create_minimal_pdf("Asus Purchase Invoice 2024")
    client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("invoice.pdf", inv_pdf, "application/pdf")},
        data={"evidence_type": "INVOICE"},
    )
    # Upload REPAIR_RECEIPT (WARRANTY is NOT uploaded)
    rec_pdf = create_minimal_pdf("Service Center Job Sheet 1")
    client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("job_sheet.pdf", rec_pdf, "application/pdf")},
        data={"evidence_type": "REPAIR_RECEIPT"},
    )

    # Ingest provider response offering replacement
    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "We acknowledge repeat repairs. Replacement authorized for the defective laptop unit.",
            "provider_name": "Asus Service",
        },
    )
    resp_id = sim_resp.json()["id"]
    client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")

    wf = client.get(f"/api/cases/{case_id}/workflow-state").json()
    # Missing warranty must NOT block workflow
    assert "Warranty" not in str(wf["pending_evidence"])
    assert wf["pending_evidence"] == []


def test_no_pending_evidence_does_not_produce_generic_upload_request(client: TestClient):
    """
    Test 2: When no blocking evidence is pending, the workflow recommendation
    must NOT generically ask the user to upload documents.
    """
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "No Generic Upload Request Test",
            "product_name": "Bose QuietComfort 45",
            "issue_description": "Right earcup buzz.",
        },
    )
    case_id = create_resp.json()["id"]

    # Upload INVOICE
    inv_pdf = create_minimal_pdf("Bose Purchase Invoice")
    client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("invoice.pdf", inv_pdf, "application/pdf")},
        data={"evidence_type": "INVOICE"},
    )

    # Ingest response with replacement commitment
    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Replacement authorized for defective headset assembly.",
            "provider_name": "Bose Support",
        },
    )
    resp_id = sim_resp.json()["id"]
    proc_resp = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    act_id = proc_resp.json()["workflow_state"]["active_action_id"]

    # Approve and execute action so no action is pending
    if act_id:
        appr = client.post(f"/api/actions/{act_id}/approve")
        assert appr.status_code == status.HTTP_200_OK
        exec_resp = client.post(f"/api/actions/{act_id}/execute")
        assert exec_resp.status_code == status.HTTP_200_OK

    wf = client.get(f"/api/cases/{case_id}/workflow-state").json()
    assert wf["pending_evidence"] == []
    # Must NOT ask generically to upload documents
    rec = wf["latest_recommendation"].lower()
    assert "upload supporting documentation" not in rec
    assert "upload requested documentation" not in rec
    assert "replacement authorization" in rec or "resolution terms" in rec


def test_active_provider_offer_leads_to_resolution_review_step(client: TestClient):
    """
    Test 3: Active provider offer (replacement authorization) with no pending action
    leads to an UNDER_REVIEW / NONE state recommending the user review terms,
    without marking the case resolved or guaranteeing replacement.
    """
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Provider Offer Next Step Test",
            "product_name": "Pixel 8 Pro",
            "issue_description": "Green screen line failure.",
        },
    )
    case_id = create_resp.json()["id"]

    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Claim verified. Replacement authorized for customer handset.",
            "provider_name": "Google Repair Hub",
        },
    )
    resp_id = sim_resp.json()["id"]
    proc_resp = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    act_id = proc_resp.json()["workflow_state"]["active_action_id"]

    # Execute action to test subsequent state
    if act_id:
        appr = client.post(f"/api/actions/{act_id}/approve")
        assert appr.status_code == status.HTTP_200_OK
        exec_resp = client.post(f"/api/actions/{act_id}/execute")
        assert exec_resp.status_code == status.HTTP_200_OK

    wf = client.get(f"/api/cases/{case_id}/workflow-state").json()
    assert wf["stage"] == "UNDER_REVIEW"
    assert wf["wait_state"] == "NONE"
    assert "replacement authorization" in wf["latest_recommendation"].lower()
    assert "review the available resolution terms" in wf["latest_recommendation"].lower()

    # Case must NOT be marked resolved and no claim that replacement is guaranteed
    case_data = client.get(f"/api/cases/{case_id}").json()
    assert case_data["status"] != "RESOLVED"


def test_explicitly_requested_evidence_remains_blocking_until_satisfied(client: TestClient):
    """
    Test 4: When a provider explicitly requests warranty documentation,
    it remains blocking in pending_evidence until satisfied by evidence upload.
    """
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Explicit Warranty Request Test",
            "product_name": "LG OLED TV",
            "issue_description": "Dead pixel cluster.",
        },
    )
    case_id = create_resp.json()["id"]

    # Provider explicitly requests warranty card
    sim_resp = client.post(
        f"/api/cases/{case_id}/simulate-response",
        json={
            "response_text": "Please provide your warranty card and proof of warranty certificate to evaluate coverage.",
            "provider_name": "LG Service Center",
        },
    )
    resp_id = sim_resp.json()["id"]
    proc_resp = client.post(f"/api/cases/{case_id}/responses/{resp_id}/process")
    wf_proc = proc_resp.json()["workflow_state"]

    assert wf_proc["stage"] == "EVIDENCE_GATHERING"
    assert wf_proc["wait_state"] == "WAITING_FOR_USER_INPUT"
    assert any("warranty" in e.lower() for e in wf_proc["pending_evidence"])

    # Upload WARRANTY document to satisfy requirement
    warranty_pdf = create_minimal_pdf("LG Manufacturer Extended Warranty Certificate")
    upload_resp = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("warranty.pdf", warranty_pdf, "application/pdf")},
        data={"evidence_type": "WARRANTY"},
    )
    assert upload_resp.status_code == status.HTTP_201_CREATED

    wf_after = client.get(f"/api/cases/{case_id}/workflow-state").json()
    assert not any("warranty" in e.lower() for e in wf_after["pending_evidence"])

