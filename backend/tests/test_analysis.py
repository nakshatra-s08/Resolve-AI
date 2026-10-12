import uuid
from fastapi import status
from fastapi.testclient import TestClient
from tests.test_evidence import create_minimal_pdf


def test_case_analysis_demo_mode_without_evidence(client: TestClient):
    """POST /api/cases/{case_id}/analysis generates structured recommendation highlighting missing evidence."""
    # 1. Create a case
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Laptop Repair Failure",
            "product_name": "Dell XPS 15",
            "issue_description": "Motherboard failed twice; display flickering continues after service visits.",
        },
    )
    case_id = create_resp.json()["id"]

    # 2. Run analysis
    analysis_resp = client.post(f"/api/cases/{case_id}/analysis")
    assert analysis_resp.status_code == status.HTTP_200_OK
    data = analysis_resp.json()

    assert data["case_id"] == case_id
    assert data["engine_mode"] == "demo"
    assert "Dell XPS 15" in data["summary"]
    assert len(data["known_facts"]) >= 1
    assert any(f["category"] == "USER_REPORTED" for f in data["known_facts"])

    # Without receipts, recommendation must flag missing repair receipt/job sheet
    assert len(data["missing_information"]) > 0
    missing_items = [m["item"] for m in data["missing_information"]]
    assert any("Repair" in m for m in missing_items)

    # Citations must reference actual policy sources
    assert len(data["supporting_policy_sources"]) > 0
    for policy in data["supporting_policy_sources"]:
        assert policy["source_id"].startswith("policy_")

    # Uncertainty notes present
    assert len(data["uncertainty_notes"]) >= 2

    # Status must NOT have changed automatically
    case_check = client.get(f"/api/cases/{case_id}").json()
    assert case_check["status"] == "NEW"

    # Timeline event was logged
    timeline = client.get(f"/api/cases/{case_id}/timeline").json()
    assert any(e["event_type"] == "SYSTEM_EVENT" for e in timeline)


def test_case_analysis_adapts_when_evidence_attached(client: TestClient):
    """Analysis recommendation changes when invoice and repair receipts are uploaded."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Laptop Repair Failure",
            "product_name": "MacBook Air",
            "issue_description": "Keyboard logic board defective twice.",
        },
    )
    case_id = create_resp.json()["id"]

    # Upload INVOICE
    pdf_inv = create_minimal_pdf("Apple Store Tax Invoice Total $1200")
    client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("invoice.pdf", pdf_inv, "application/pdf")},
        data={"evidence_type": "INVOICE"},
    )

    # Upload REPAIR_RECEIPT
    pdf_rec = create_minimal_pdf("Authorized Service Job Sheet Repair 1 and 2")
    client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("repair_receipt.pdf", pdf_rec, "application/pdf")},
        data={"evidence_type": "REPAIR_RECEIPT"},
    )

    analysis_resp = client.post(f"/api/cases/{case_id}/analysis")
    assert analysis_resp.status_code == status.HTTP_200_OK
    data = analysis_resp.json()

    # Evidence considered
    assert len(data["evidence_considered"]) == 2
    # Extracted text should appear in known facts
    assert any(f["category"] == "EXTRACTED_FROM_DOCUMENT" for f in data["known_facts"])
    # With receipts attached, recommended step pivots towards formal replacement/escalation
    assert any(w in data["recommended_next_step"].lower() for w in ["escalation", "replacement", "refund"])


def test_case_analysis_unknown_case_returns_404(client: TestClient):
    """Analysis on unknown case returns 404."""
    unknown_id = str(uuid.uuid4())
    resp = client.post(f"/api/cases/{unknown_id}/analysis")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_case_chat_endpoint(client: TestClient):
    """POST /api/cases/{case_id}/chat returns grounded answer citing case and policy."""
    create_resp = client.post(
        "/api/cases",
        json={
            "title": "Chat Case",
            "product_name": "Lenovo ThinkPad",
            "issue_description": "Fan grinding noise returns after servicing.",
        },
    )
    case_id = create_resp.json()["id"]

    chat_resp = client.post(
        f"/api/cases/{case_id}/chat",
        json={"message": "What should my next step be regarding replacement policy?"},
    )
    assert chat_resp.status_code == status.HTTP_200_OK
    data = chat_resp.json()
    assert data["case_id"] == case_id
    assert data["engine_mode"] == "demo"
    assert "Lenovo ThinkPad" in data["answer"]
    assert len(data["distinction_notes"]) > 0
    assert len(data["supporting_policy_sources"]) > 0


def test_case_chat_rejects_empty_message(client: TestClient):
    """Chat rejects empty or whitespace-only message."""
    create_resp = client.post(
        "/api/cases",
        json={"title": "Chat Case", "product_name": "Device", "issue_description": "Issue"},
    )
    case_id = create_resp.json()["id"]

    resp = client.post(f"/api/cases/{case_id}/chat", json={"message": "   "})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_case_chat_unknown_case_returns_404(client: TestClient):
    """Chat on unknown case returns 404."""
    unknown_id = str(uuid.uuid4())
    resp = client.post(f"/api/cases/{unknown_id}/chat", json={"message": "Hello"})
    assert resp.status_code == status.HTTP_404_NOT_FOUND
