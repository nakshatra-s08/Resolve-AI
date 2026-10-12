import io
import uuid
from pathlib import Path
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pypdf import PdfWriter


def create_minimal_pdf(text: str = "") -> bytes:
    """Generate a valid in-memory PDF, optionally with text."""
    # Build a simple valid PDF using pypdf or minimal raw PDF syntax
    # Since pypdf is installed, let's create a minimal valid PDF with /Type /Page
    # A standard raw PDF stream is reliable and fast:
    content_stream = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET" if text else ""
    stream_len = len(content_stream.encode("latin-1"))
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length " + str(stream_len).encode("latin-1") + b" >>\nstream\n"
        + content_stream.encode("latin-1") + b"\nendstream\nendobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000244 00000 n \n"
        b"0000000330 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n412\n%%EOF"
    )
    return pdf


def create_sample_png() -> bytes:
    """Minimal valid 1x1 PNG."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_upload_pdf_with_text_extraction(client: TestClient):
    """Uploading a PDF extracts selectable text and classifies category."""
    # 1. Create a case
    case_resp = client.post(
        "/api/cases",
        json={
            "title": "Evidence Test Case",
            "product_name": "Laptop",
            "issue_description": "Motherboard issue",
        },
    )
    case_id = case_resp.json()["id"]

    # 2. Upload PDF
    pdf_bytes = create_minimal_pdf("Laptop Repair Invoice 12345")
    response = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("laptop_repair_invoice.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["case_id"] == case_id
    assert data["original_filename"] == "laptop_repair_invoice.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["evidence_type"] == "INVOICE"
    assert data["extraction_status"] == "COMPLETED"
    assert "Laptop Repair Invoice 12345" in data["extracted_text"]


def test_upload_image_handling(client: TestClient):
    """Supported images upload with UNSUPPORTED extraction status (no OCR)."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Img Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    png_bytes = create_sample_png()
    response = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("service_photo.png", png_bytes, "image/png")},
        data={"evidence_type": "OTHER"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["evidence_type"] == "OTHER"
    assert data["extraction_status"] == "UNSUPPORTED"
    assert data["extracted_text"] is None


def test_upload_rejects_unsupported_extension(client: TestClient):
    """Files with unsupported extensions like .exe or .txt are rejected."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    response = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("script.sh", b"echo hello", "text/plain")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unsupported file extension" in response.json()["detail"]


def test_upload_rejects_empty_file(client: TestClient):
    """Empty 0-byte uploads are rejected."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    response = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "empty" in response.json()["detail"].lower()


def test_upload_rejects_mismatched_content_header(client: TestClient):
    """Reject file when file content does not match declared extension."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    response = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("fake.pdf", b"NOT_A_REAL_PDF_HEADER", "application/pdf")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "do not match declared extension" in response.json()["detail"]


def test_upload_rejects_unknown_case_id(client: TestClient):
    """Upload to a non-existent case returns 404."""
    unknown_id = str(uuid.uuid4())
    pdf_bytes = create_minimal_pdf("Test")
    response = client.post(
        f"/api/cases/{unknown_id}/evidence",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_upload_path_traversal_sanitization(client: TestClient):
    """Filenames with path traversal characters are sanitized to safe basenames."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    pdf_bytes = create_minimal_pdf("Test")
    response = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("../../etc/passwd.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert ".." not in data["original_filename"]
    assert "/" not in data["original_filename"]


def test_list_and_get_evidence(client: TestClient):
    """GET /api/cases/{case_id}/evidence lists metadata without extracted text, detail includes text."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    pdf_bytes = create_minimal_pdf("Detailed Warranty Document")
    up_resp = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("warranty_card.pdf", pdf_bytes, "application/pdf")},
        data={"evidence_type": "WARRANTY"},
    )
    ev_id = up_resp.json()["id"]

    # 1. List
    list_resp = client.get(f"/api/cases/{case_id}/evidence")
    assert list_resp.status_code == status.HTTP_200_OK
    items = list_resp.json()
    assert len(items) == 1
    assert items[0]["id"] == ev_id
    assert "extracted_text" not in items[0]  # Omitted in summary list

    # 2. Detail
    detail_resp = client.get(f"/api/cases/{case_id}/evidence/{ev_id}")
    assert detail_resp.status_code == status.HTTP_200_OK
    detail = detail_resp.json()
    assert detail["id"] == ev_id
    assert "Detailed Warranty Document" in detail["extracted_text"]


def test_delete_evidence_and_file_cleanup(client: TestClient):
    """DELETE /api/cases/{case_id}/evidence/{evidence_id} removes DB record, removes file, and logs event."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    pdf_bytes = create_minimal_pdf("To be deleted")
    up_resp = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("receipt.pdf", pdf_bytes, "application/pdf")},
    )
    ev_id = up_resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/api/cases/{case_id}/evidence/{ev_id}")
    assert del_resp.status_code == status.HTTP_200_OK

    # Detail now returns 404
    get_resp = client.get(f"/api/cases/{case_id}/evidence/{ev_id}")
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    # Timeline records EVIDENCE_DELETED event
    t_resp = client.get(f"/api/cases/{case_id}/timeline")
    events = t_resp.json()
    event_types = [e["event_type"] for e in events]
    assert "EVIDENCE_UPLOADED" in event_types
    assert "EVIDENCE_DELETED" in event_types


def test_evidence_checklist_response(client: TestClient):
    """GET /api/cases/{case_id}/evidence-checklist reflects existing vs missing categories."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Checklist Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    # Initial checklist: all 4 missing
    c1 = client.get(f"/api/cases/{case_id}/evidence-checklist").json()
    assert len(c1["represented_categories"]) == 0
    assert len(c1["missing_categories"]) == 4

    # Upload INVOICE
    pdf_bytes = create_minimal_pdf("Invoice 100")
    client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("inv.pdf", pdf_bytes, "application/pdf")},
        data={"evidence_type": "INVOICE"},
    )

    c2 = client.get(f"/api/cases/{case_id}/evidence-checklist").json()
    assert "INVOICE" in c2["represented_categories"]
    assert "INVOICE" not in c2["missing_categories"]
    assert "WARRANTY" in c2["missing_categories"]
    assert "completeness aid" in c2["explanation"].lower()


def test_malformed_pdf_graceful_handling(client: TestClient):
    """Malformed PDF does not crash app; extraction_status is FAILED."""
    case_resp = client.post(
        "/api/cases",
        json={"title": "Corrupt Case", "product_name": "Device", "issue_description": "Defect"},
    )
    case_id = case_resp.json()["id"]

    # Pass %PDF header followed by corrupted garbage
    corrupt_pdf = b"%PDF-1.4\nCorrupted binary garbage without catalog or xref\n%%EOF"
    response = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("corrupt.pdf", corrupt_pdf, "application/pdf")},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["extraction_status"] == "FAILED"
    assert data["extracted_text"] is None
