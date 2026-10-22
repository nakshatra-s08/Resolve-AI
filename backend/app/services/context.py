from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.case import Case
from app.models.event import CaseEvent
from app.models.evidence import Evidence, ExtractionStatus, EvidenceType
from app.models.response import SimulatedResponse, ResponseProcessingStatus

BASELINE_CHECKLIST = [
    EvidenceType.INVOICE,
    EvidenceType.WARRANTY,
    EvidenceType.REPAIR_RECEIPT,
    EvidenceType.SERVICE_COMMUNICATION,
]


class CaseContextService:
    """Gathers and filters case details, timeline, readable evidence, and responses into structured context."""

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

        from app.services.extractor import assess_evidence_relevance, sanitize_extracted_snippet

        evidence_items = []
        represented_categories = set()

        for ev in evidence_records:
            represented_categories.add(ev.evidence_type)
            rel_status, rel_reason = assess_evidence_relevance(
                filename=ev.original_filename,
                extracted_text=ev.extracted_text,
                product_name=case.product_name,
                issue_description=case.issue_description,
            )

            item = {
                "id": ev.id,
                "filename": ev.original_filename,
                "type": ev.evidence_type.value,
                "extraction_status": ev.extraction_status.value,
                "relevance_status": rel_status,
                "relevance_reason": rel_reason,
                "extracted_text_snippet": None,
            }
            # Only include extracted text if extraction was COMPLETED and not a confirmed MISMATCH
            if ev.extraction_status == ExtractionStatus.COMPLETED and ev.extracted_text and rel_status != "MISMATCH":
                # Sanitize to prevent leaking addresses/emails/phone numbers
                item["extracted_text_snippet"] = sanitize_extracted_snippet(ev.extracted_text, max_chars=400)

            evidence_items.append(item)

        missing_categories = [
            cat.value for cat in BASELINE_CHECKLIST if cat not in represented_categories
        ]

        # Fetch simulated provider responses
        responses = (
            self.db.query(SimulatedResponse)
            .filter(SimulatedResponse.case_id == case_id)
            .order_by(SimulatedResponse.created_at.desc())
            .all()
        )
        response_summaries = [
            {
                "id": r.id,
                "provider_name": r.provider_name,
                "status": r.status.value,
                "response_text": r.response_text[:500],
                "created_at": r.created_at.isoformat(),
            }
            for r in responses
        ]

        # Extract identified provider commitments
        commitments = []
        for r in responses:
            if r.processing_result_json and isinstance(r.processing_result_json, dict):
                comms = r.processing_result_json.get("identified_commitments") or []
                for c in comms:
                    if c not in commitments:
                        commitments.append(c)

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
            "represented_categories": [
                category.value for category in BASELINE_CHECKLIST if category in represented_categories
            ],
            "missing_categories": missing_categories,
            "responses": response_summaries,
            "commitments": commitments,
            "suggested_query": search_query,
        }
