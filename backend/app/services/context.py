from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.case import Case
from app.models.event import CaseEvent
from app.models.evidence import Evidence, ExtractionStatus, EvidenceType

BASELINE_CHECKLIST = [
    EvidenceType.INVOICE,
    EvidenceType.WARRANTY,
    EvidenceType.REPAIR_RECEIPT,
    EvidenceType.SERVICE_COMMUNICATION,
]


class CaseContextService:
    """Gathers and filters case details, timeline, and readable evidence into structured context."""

    def __init__(self, db: Session):
        self.db = db

    def assemble_context(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Assemble structured context bundle for a case."""
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return None

        # Fetch chronological events
        events = (
            self.db.query(CaseEvent)
            .filter(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.created_at.asc(), CaseEvent.id.asc())
            .all()
        )

        timeline_summary = [
            {
                "timestamp": e.created_at.isoformat(),
                "event_type": e.event_type.value,
                "description": e.description,
                "source": e.source_type.value,
            }
            for e in events
        ]

        # Fetch evidence items
        evidence_records = (
            self.db.query(Evidence)
            .filter(Evidence.case_id == case_id)
            .order_by(Evidence.created_at.desc())
            .all()
        )

        evidence_items = []
        represented_categories = set()

        for ev in evidence_records:
            represented_categories.add(ev.evidence_type)
            item = {
                "id": ev.id,
                "filename": ev.original_filename,
                "type": ev.evidence_type.value,
                "extraction_status": ev.extraction_status.value,
                "extracted_text_snippet": None,
            }
            # Only include extracted text if extraction was COMPLETED
            if ev.extraction_status == ExtractionStatus.COMPLETED and ev.extracted_text:
                # Bounded snippet (first 1000 characters) to avoid prompt bloat
                item["extracted_text_snippet"] = ev.extracted_text[:1000]

            evidence_items.append(item)

        missing_categories = [
            cat.value for cat in BASELINE_CHECKLIST if cat not in represented_categories
        ]

        # Synthesize search query for policy retrieval
        search_query = f"{case.product_name} {case.issue_description} repeat repair failure"

        return {
            "case_id": case.id,
            "title": case.title,
            "product_name": case.product_name,
            "issue_description": case.issue_description,
            "status": case.status.value,
            "created_at": case.created_at.isoformat(),
            "updated_at": case.updated_at.isoformat(),
            "timeline": timeline_summary,
            "evidence": evidence_items,
            "represented_categories": [c.value for c in represented_categories],
            "missing_categories": missing_categories,
            "suggested_query": search_query,
        }
