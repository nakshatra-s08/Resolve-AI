from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.models.case import Case, CaseStatus
from app.models.response import SimulatedResponse
from app.models.action import Action, ActionType, ActionStatus
from app.schemas.policy import PolicySearchResultItem
from app.schemas.response import ResponseProcessingResult
from app.services.retrieval import PolicyRetrievalService


class ResponseProcessingService:
    """Processes simulated service provider responses in the context of the case."""

    def __init__(self, db):
        self.db = db

    def process_response(
        self,
        case: Case,
        response: SimulatedResponse,
        context: Dict[str, Any],
        retrieved_policies: List[PolicySearchResultItem],
    ) -> ResponseProcessingResult:
        """
        Analyze a simulated provider response deterministically against existing evidence and case state.
        Returns a structured ResponseProcessingResult.
        """
        now = datetime.now(timezone.utc)
        text = response.response_text
        text_lower = text.lower()

        # Identify requested information or documents
        requested_info = []
        evidence_still_needed = []
        evidence_already_available = []

        rep_categories = set(context.get("represented_categories", []))

        # Check for repair receipts / job sheet requests
        if any(w in text_lower for w in ["job sheet", "repair receipt", "service record", "work order"]):
            requested_info.append("Prior service job sheets / repair receipts")
            if "REPAIR_RECEIPT" in rep_categories:
                evidence_already_available.append("Prior repair receipt (already attached to case)")
            else:
                evidence_still_needed.append("Prior repair receipts / job sheets")

        # Check for invoice / purchase proof requests
        if any(w in text_lower for w in ["invoice", "proof of purchase", "bill", "purchase date"]):
            requested_info.append("Original purchase invoice / proof of purchase")
            if "INVOICE" in rep_categories:
                evidence_already_available.append("Purchase invoice (already attached to case)")
            else:
                evidence_still_needed.append("Original purchase invoice")

        # Check for warranty card / documentation requests
        if any(w in text_lower for w in ["warranty card", "warranty document", "warranty certificate", "proof of warranty", "copy of warranty"]):
            requested_info.append("Warranty documentation / card")
            if "WARRANTY" in rep_categories:
                evidence_already_available.append("Warranty document (already attached to case)")
            else:
                evidence_still_needed.append("Warranty documentation / card")

        # Check for date or diagnostic details requested
        if any(w in text_lower for w in ["exact date", "when did", "describe", "serial number"]):
            requested_info.append("Specific timeline dates / serial number confirmation")

        # Identify explicit commitments or deadlines
        commitments = []
        if any(w in text_lower for w in ["within 24 hours", "within 48 hours", "within 5 business days", "within 3 days"]):
            commitments.append("Turnaround deadline indicated by provider")
        if any(w in text_lower for w in ["approved", "agreed to replace", "replacement authorized"]):
            commitments.append("Replacement authorization offered")
        elif any(w in text_lower for w in ["refund will be issued", "credit note"]):
            commitments.append("Refund or credit note commitment offered")

        # Identify ambiguities or non-committal statements
        ambiguities = []
        if any(w in text_lower for w in ["will consider", "might", "subject to review", "cannot guarantee", "as per policy"]):
            ambiguities.append("Provider response contains non-committal or contingent phrasing")
        if not commitments and not requested_info:
            ambiguities.append("Response is generic without clear next steps or commitments")

        # Determine suggested next case status and action
        suggested_status = None
        suggested_action = None

        if evidence_still_needed:
            # Missing evidence requested by provider
            summary = (
                f"Simulated provider requested additional evidence ({', '.join(evidence_still_needed)}). "
                "Case should move to COLLECTING_EVIDENCE."
            )
            recommended_step = (
                f"Upload requested documentation ({', '.join(evidence_still_needed)}) to satisfy the service center inquiry."
            )
            suggested_status = CaseStatus.COLLECTING_EVIDENCE.value
            suggested_action = {
                "action_type": "SCHEDULE_FOLLOW_UP",
                "title": "Follow up after document upload",
                "description": "Ensure requested documents are submitted and re-evaluated by the provider.",
                "payload": {
                    "due_at": (now.replace(microsecond=0)).isoformat(),
                    "purpose": f"Submit {', '.join(evidence_still_needed)} to provider",
                },
            }
        elif commitments:
            # Commitments found
            summary = (
                "Simulated provider provided an actionable commitment or response. "
                "Case is ready for review."
            )
            recommended_step = (
                "Review the provider commitment against warranty guidelines and confirm next steps with customer."
            )
            suggested_status = CaseStatus.UNDER_REVIEW.value
            suggested_action = {
                "action_type": "SEND_MESSAGE",
                "title": "Acknowledge Provider Commitment",
                "description": "Send formal acknowledgment confirming terms offered by the service center.",
                "payload": {
                    "recipient": response.provider_name,
                    "subject": "Acknowledgment of Resolution Terms",
                    "message_body": "Thank you for confirming the proposed resolution. Please proceed as agreed.",
                    "is_simulated": True,
                },
            }
        else:
            # General response under review
            summary = (
                f"Simulated response received from {response.provider_name}. "
                "Evaluated against case timeline and existing evidence."
            )
            recommended_step = (
                "Provide clarification or restate the repeated repair failure history under warranty guidelines."
            )
            suggested_status = CaseStatus.UNDER_REVIEW.value
            suggested_action = {
                "action_type": "SEND_MESSAGE",
                "title": "Clarification Response to Provider",
                "description": "Respond to service center clarifying recurrence of defect.",
                "payload": {
                    "recipient": response.provider_name,
                    "subject": f"Clarification - Repair Case {case.id[:8]}",
                    "message_body": "Following up on your response: the device experienced the identical defect after two previous repairs.",
                    "is_simulated": True,
                },
            }

        uncertainty_notes = [
            "This response processing was performed in DEMO MODE using deterministic rules.",
            "The provider response is simulated and does not represent an actual manufacturer email or letter.",
            "No resolution or warranty entitlement is legally binding until confirmed in writing.",
        ]

        return ResponseProcessingResult(
            case_id=case.id,
            response_id=response.id,
            engine_mode="demo",
            summary=summary,
            requested_information=requested_info,
            identified_commitments=commitments,
            ambiguities=ambiguities,
            evidence_already_available=evidence_already_available,
            evidence_still_needed=evidence_still_needed,
            recommended_next_step=recommended_step,
            supporting_policy_sources=retrieved_policies,
            uncertainty_notes=uncertainty_notes,
            suggested_action=suggested_action,
            suggested_case_status=suggested_status,
            processed_at=now,
        )
