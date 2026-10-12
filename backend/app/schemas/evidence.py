from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict, Field
from app.models.evidence import EvidenceType, ExtractionStatus


class EvidenceRead(BaseModel):
    """Schema for listing evidence items (omits complete extracted text for brevity)."""
    id: str
    case_id: str
    original_filename: str
    evidence_type: EvidenceType
    mime_type: str
    file_size_bytes: int
    extraction_status: ExtractionStatus
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "2d17cba5-97c1-4cfa-9eb9-b82875b1191c",
                "case_id": "e3a89047-36e2-45e0-8bc2-a279144ce10e",
                "original_filename": "laptop_repair_invoice.pdf",
                "evidence_type": "INVOICE",
                "mime_type": "application/pdf",
                "file_size_bytes": 104523,
                "extraction_status": "COMPLETED",
                "created_at": "2026-10-12T10:15:00Z",
            }
        },
    )


class EvidenceDetail(EvidenceRead):
    """Schema for detailed view of a single evidence item, including extracted text."""
    extracted_text: Optional[str] = None
    suggested_evidence_type: Optional[EvidenceType] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "2d17cba5-97c1-4cfa-9eb9-b82875b1191c",
                "case_id": "e3a89047-36e2-45e0-8bc2-a279144ce10e",
                "original_filename": "laptop_repair_invoice.pdf",
                "evidence_type": "INVOICE",
                "suggested_evidence_type": "INVOICE",
                "mime_type": "application/pdf",
                "file_size_bytes": 104523,
                "extracted_text": "TAX INVOICE\nItem: Dell Motherboard Service\nAmount: $0.00 (Warranty)",
                "extraction_status": "COMPLETED",
                "created_at": "2026-10-12T10:15:00Z",
            }
        },
    )


class EvidenceChecklistResponse(BaseModel):
    """Response schema summarizing available vs missing evidence categories."""
    represented_categories: List[EvidenceType]
    missing_categories: List[EvidenceType]
    explanation: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "represented_categories": ["INVOICE", "REPAIR_RECEIPT"],
                "missing_categories": ["WARRANTY", "SERVICE_COMMUNICATION"],
                "explanation": (
                    "This checklist is a heuristic completeness aid to help organize your case. "
                    "Missing categories do not legally invalidate a claim or complaint."
                ),
            }
        }
    )
