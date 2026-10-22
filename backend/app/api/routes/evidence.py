from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.case import Case
from app.models.event import CaseEvent, EventType, EventSource
from app.models.evidence import Evidence, EvidenceType, ExtractionStatus
from app.schemas.evidence import EvidenceRead, EvidenceDetail, EvidenceChecklistResponse
from app.services.storage import (
    save_uploaded_file,
    remove_stored_file,
    stage_stored_file_for_deletion,
    restore_staged_file,
    discard_staged_file,
)
from app.services.extractor import extract_text_from_file, classify_document
from app.services.orchestrator import OrchestrationService

router = APIRouter(prefix="/cases/{case_id}", tags=["Evidence"])

BASELINE_CATEGORIES = [
    EvidenceType.INVOICE,
    EvidenceType.WARRANTY,
    EvidenceType.REPAIR_RECEIPT,
    EvidenceType.SERVICE_COMMUNICATION,
]


@router.post(
    "/evidence",
    response_model=EvidenceDetail,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(..., description="Uploaded document or image"),
    evidence_type: Optional[EvidenceType] = Form(None, description="Optional category"),
    db: Session = Depends(get_db),
) -> EvidenceDetail:
    """Upload evidence for a case, extract text where supported, and record a timeline event."""
    # Verify case exists
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    # Save file safely to storage
    orig_name, storage_name, file_size, rel_path, ext, content = await save_uploaded_file(file)

    # Extract text
    mime_type = file.content_type or f"application/{ext}"
    extracted_text, extraction_status = extract_text_from_file(content, mime_type, ext)

    # Suggest category heuristic
    suggested_type = classify_document(orig_name, extracted_text)
    # Classification is advisory only. Without an explicit user-selected category,
    # do not let a filename or text heuristic count as a represented checklist item.
    assigned_type = evidence_type if evidence_type is not None else EvidenceType.OTHER

    # Persist in database
    db_evidence = Evidence(
        case_id=case_id,
        original_filename=orig_name,
        storage_filename=storage_name,
        relative_storage_path=rel_path,
        mime_type=mime_type,
        file_extension=ext,
        file_size_bytes=file_size,
        evidence_type=assigned_type,
        extracted_text=extracted_text,
        extraction_status=extraction_status,
    )

    try:
        db.add(db_evidence)
        db.flush()

        # Record timeline event without dumping sensitive extracted text
        event = CaseEvent(
            case_id=case_id,
            event_type=EventType.EVIDENCE_UPLOADED,
            description=f"Evidence uploaded: '{orig_name}' (Category: {assigned_type.value}).",
            source_type=EventSource.USER,
            metadata_json={
                "evidence_id": db_evidence.id,
                "filename": orig_name,
                "evidence_type": assigned_type.value,
                "file_size_bytes": file_size,
                "extraction_status": extraction_status.value,
            },
        )
        db.add(event)
        db.flush()
        orchestrator = OrchestrationService(db)
        orchestrator.reassess_case(db_case.id, record_event=False)
        db.commit()
        db.refresh(db_evidence)

    except Exception as exc:
        db.rollback()
        # Clean up file on disk if DB transaction fails
        remove_stored_file(storage_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record evidence in database.",
        ) from exc

    return EvidenceDetail(
        id=db_evidence.id,
        case_id=db_evidence.case_id,
        original_filename=db_evidence.original_filename,
        evidence_type=db_evidence.evidence_type,
        suggested_evidence_type=suggested_type,
        mime_type=db_evidence.mime_type,
        file_size_bytes=db_evidence.file_size_bytes,
        extracted_text=db_evidence.extracted_text,
        extraction_status=db_evidence.extraction_status,
        created_at=db_evidence.created_at,
    )


@router.get("/evidence", response_model=List[EvidenceRead])
def list_case_evidence(case_id: str, db: Session = Depends(get_db)) -> List[Evidence]:
    """List all evidence attached to a case (without complete extracted text)."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    return (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.created_at.desc(), Evidence.id.desc())
        .all()
    )


@router.get("/evidence/{evidence_id}", response_model=EvidenceDetail)
def get_case_evidence_detail(
    case_id: str,
    evidence_id: str,
    db: Session = Depends(get_db),
) -> EvidenceDetail:
    """Retrieve details and extracted text for an evidence record."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    db_evidence = (
        db.query(Evidence)
        .filter(Evidence.id == evidence_id, Evidence.case_id == case_id)
        .first()
    )
    if not db_evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' was not found for this case.",
        )

    suggested = classify_document(db_evidence.original_filename, db_evidence.extracted_text)
    return EvidenceDetail(
        id=db_evidence.id,
        case_id=db_evidence.case_id,
        original_filename=db_evidence.original_filename,
        evidence_type=db_evidence.evidence_type,
        suggested_evidence_type=suggested,
        mime_type=db_evidence.mime_type,
        file_size_bytes=db_evidence.file_size_bytes,
        extracted_text=db_evidence.extracted_text,
        extraction_status=db_evidence.extraction_status,
        created_at=db_evidence.created_at,
    )


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_200_OK)
def delete_case_evidence(
    case_id: str,
    evidence_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Remove evidence metadata and underlying stored file, recording a timeline event."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    db_evidence = (
        db.query(Evidence)
        .filter(Evidence.id == evidence_id, Evidence.case_id == case_id)
        .first()
    )
    if not db_evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' was not found for this case.",
        )

    # Stage the file with an atomic rename. If the database commit fails, restore it.
    storage_name = db_evidence.storage_filename
    orig_name = db_evidence.original_filename
    staged_name = stage_stored_file_for_deletion(storage_name)
    if staged_name is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stage stored file for deletion.",
        )

    # Delete record from database and record timeline event
    event = CaseEvent(
        case_id=case_id,
        event_type=EventType.EVIDENCE_DELETED,
        description=f"Evidence removed: '{orig_name}'.",
        source_type=EventSource.USER,
        metadata_json={
            "evidence_id": evidence_id,
            "filename": orig_name,
        },
    )
    db.add(event)
    db.delete(db_evidence)
    db.flush()
    try:
        orchestrator = OrchestrationService(db)
        orchestrator.reassess_case(case_id, record_event=False)
        db.commit()
    except Exception as exc:
        db.rollback()
        restored = restore_staged_file(storage_name, staged_name)
        message = "Failed to remove evidence from database."
        if not restored:
            message += " File restoration also failed; recover the staged file manually."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc

    if not discard_staged_file(staged_name):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evidence metadata was removed, but the staged file could not be cleaned up.",
        )

    return {"status": "success", "message": f"Evidence '{orig_name}' removed successfully."}


@router.get("/evidence-checklist", response_model=EvidenceChecklistResponse)
def get_evidence_checklist(
    case_id: str,
    db: Session = Depends(get_db),
) -> EvidenceChecklistResponse:
    """Summarize represented vs missing evidence categories for a case."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    existing_types = {
        row[0]
        for row in db.query(Evidence.evidence_type)
        .filter(Evidence.case_id == case_id)
        .all()
    }

    represented = [cat for cat in BASELINE_CATEGORIES if cat in existing_types]
    missing = [cat for cat in BASELINE_CATEGORIES if cat not in existing_types]

    explanation = (
        "This checklist measures document category coverage as an organizational completeness aid. "
        "Category presence does not verify the quality, authenticity, or case relevance of uploaded documents. "
        "Missing categories do not legally invalidate a claim or grievance."
    )

    return EvidenceChecklistResponse(
        represented_categories=represented,
        missing_categories=missing,
        explanation=explanation,
    )
