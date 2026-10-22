from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.case import Case, CaseStatus, VALID_STATUS_TRANSITIONS, get_utc_now
from app.models.event import CaseEvent, EventType, EventSource
from app.models.action import Action, ActionType, ActionStatus
from app.models.evidence import Evidence
from app.models.response import SimulatedResponse, ResponseProcessingStatus
from app.models.workflow import CaseWorkflowState, WorkflowStage, WorkflowWaitState
from app.schemas.response import ResponseProcessingResult
from app.services.context import CaseContextService
from app.services.retrieval import PolicyRetrievalService


class OrchestrationService:
    """
    Dedicated agentic orchestration service for ResolveAI.
    Coordinates case reassessment, workflow state transitions, and next-step decisions.
    Ensures safe, bounded, and persistent state management without recursive execution.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_workflow_state(
        self, case: Case, auto_reassess: bool = True
    ) -> CaseWorkflowState:
        """Fetch existing workflow state or initialize a default state for the case."""
        state = (
            self.db.query(CaseWorkflowState)
            .filter(CaseWorkflowState.case_id == case.id)
            .first()
        )
        if not state:
            default_goal = (
                f"Obtain warranty resolution (repair, replacement, or refund) for {case.product_name}."
            )
            state = CaseWorkflowState(
                case_id=case.id,
                goal=default_goal,
                stage=WorkflowStage.INTAKE,
                wait_state=WorkflowWaitState.NONE,
                latest_recommendation="Initial case evaluation required.",
                pending_evidence=[],
                outstanding_commitments=[],
            )
            self.db.add(state)
            self.db.flush()
            if auto_reassess and case.status != CaseStatus.NEW:
                return self.reassess_case(case.id)
        elif (
            auto_reassess
            and state.stage == WorkflowStage.INTAKE
            and state.latest_recommendation == "Initial case evaluation required."
            and case.status != CaseStatus.NEW
        ):
            return self.reassess_case(case.id)
        elif auto_reassess and state.active_action_id:
            act = self.db.query(Action).filter(Action.id == state.active_action_id).first()
            if not act or act.status != ActionStatus.PENDING_APPROVAL:
                return self.reassess_case(case.id)
        return state

    def reassess_case(
        self,
        case_id: str,
        triggered_by_response: Optional[SimulatedResponse] = None,
        processing_result: Optional[ResponseProcessingResult] = None,
        record_event: bool = True,
    ) -> CaseWorkflowState:
        """
        Evaluate current case state, evidence, responses, and actions to produce a structured next-step decision.
        Persists updated workflow state and at most one PENDING_APPROVAL action if appropriate.
        Deterministic, bounded to a single pass, and idempotent on repeated invocations.
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case with ID '{case_id}' was not found.")

        workflow_state = self.get_or_create_workflow_state(case, auto_reassess=False)

        # Snapshot previous state for change detection (to avoid duplicate timeline events)
        prev_stage = workflow_state.stage
        prev_wait_state = workflow_state.wait_state
        prev_action_id = workflow_state.active_action_id
        prev_rec = workflow_state.latest_recommendation
        prev_pending = list(workflow_state.pending_evidence or [])

        # Check existing actions for this case
        existing_pending_action = (
            self.db.query(Action)
            .filter(Action.case_id == case_id, Action.status == ActionStatus.PENDING_APPROVAL)
            .order_by(Action.created_at.desc())
            .first()
        )

        # Extract findings from processing_result or latest processed response
        evidence_still_needed: List[str] = []
        commitments: List[str] = []
        suggested_action_dict: Optional[Dict[str, Any]] = None
        recommended_step: Optional[str] = None
        response_text: str = ""

        # Check currently attached active evidence
        active_evidence = (
            self.db.query(Evidence)
            .filter(Evidence.case_id == case_id)
            .all()
        )
        current_rep = {ev.evidence_type.value for ev in active_evidence}

        if processing_result:
            evidence_still_needed = list(processing_result.evidence_still_needed)
            commitments = list(processing_result.identified_commitments)
            suggested_action_dict = processing_result.suggested_action
            recommended_step = processing_result.recommended_next_step
            if triggered_by_response:
                response_text = triggered_by_response.response_text
        else:
            # Inspect latest processed response if available
            latest_resp = (
                self.db.query(SimulatedResponse)
                .filter(
                    SimulatedResponse.case_id == case_id,
                    SimulatedResponse.status == ResponseProcessingStatus.PROCESSED,
                )
                .order_by(SimulatedResponse.created_at.desc())
                .first()
            )
            if latest_resp and latest_resp.processing_result_json:
                res_data = latest_resp.processing_result_json
                evidence_still_needed = list(res_data.get("evidence_still_needed") or [])
                commitments = list(res_data.get("identified_commitments") or res_data.get("commitments") or [])
                suggested_action_dict = None
                recommended_step = res_data.get("recommended_next_step")
                response_text = latest_resp.response_text
            elif triggered_by_response:
                response_text = triggered_by_response.response_text

        # Filter requested documents against current active evidence to ensure dynamic consistency
        if evidence_still_needed:
            filtered_needed = []
            for req in evidence_still_needed:
                req_lower = req.lower()
                if any(w in req_lower for w in ["job sheet", "repair receipt", "service record", "work order"]):
                    if "REPAIR_RECEIPT" not in current_rep:
                        filtered_needed.append(req)
                elif any(w in req_lower for w in ["invoice", "proof of purchase", "bill", "purchase date"]):
                    if "INVOICE" not in current_rep:
                        filtered_needed.append(req)
                elif any(w in req_lower for w in ["warranty"]):
                    if "WARRANTY" not in current_rep:
                        filtered_needed.append(req)
                elif any(w in req_lower for w in ["communication", "correspondence", "email"]):
                    if "SERVICE_COMMUNICATION" not in current_rep:
                        filtered_needed.append(req)
                else:
                    filtered_needed.append(req)
            evidence_still_needed = filtered_needed

        text_lower = response_text.lower()

        # -------------------------------------------------------------
        # Decision Matrix:
        # 1. Closed or Resolved
        # 2. Provider Requesting Missing Evidence -> WAITING_FOR_USER_INPUT
        # 3. Provider Processing Internally -> WAITING_FOR_EXTERNAL_RESPONSE
        # 4. Action Justified -> WAITING_FOR_ACTION_APPROVAL (at most 1 PENDING_APPROVAL action)
        # 5. Default Review
        # -------------------------------------------------------------

        target_stage: WorkflowStage = workflow_state.stage
        target_wait_state: WorkflowWaitState = workflow_state.wait_state
        target_recommendation: Optional[str] = workflow_state.latest_recommendation
        target_pending_evidence: List[str] = list(workflow_state.pending_evidence)
        target_commitments: List[str] = list(workflow_state.outstanding_commitments)
        target_action_id: Optional[str] = workflow_state.active_action_id

        if case.status in {CaseStatus.RESOLVED, CaseStatus.CLOSED}:
            target_stage = WorkflowStage.RESOLVED if case.status == CaseStatus.RESOLVED else WorkflowStage.CLOSED
            target_wait_state = WorkflowWaitState.COMPLETED
            target_recommendation = "Case resolution achieved. No further agent action pending."
            target_action_id = None
            target_pending_evidence = []

        elif evidence_still_needed:
            # Explicit evidence requested by provider that is not yet in evidence
            target_stage = WorkflowStage.EVIDENCE_GATHERING
            target_wait_state = WorkflowWaitState.WAITING_FOR_USER_INPUT
            target_pending_evidence = evidence_still_needed
            target_commitments = commitments
            target_recommendation = (
                f"Provider requested additional documentation ({', '.join(evidence_still_needed)}). "
                "Please upload the requested documents to continue case escalation."
            )
            target_action_id = None
            # Update case status if valid transition
            self._try_transition_case_status(case, CaseStatus.COLLECTING_EVIDENCE, "missing evidence requested")

        elif existing_pending_action:
            # An action is already pending explicit user approval; reuse it to prevent duplicates
            target_stage = WorkflowStage.ACTION_PENDING
            target_wait_state = WorkflowWaitState.WAITING_FOR_ACTION_APPROVAL
            target_action_id = existing_pending_action.id
            target_recommendation = f"Review and approve proposed action: '{existing_pending_action.title}'."
            target_pending_evidence = []
            target_commitments = commitments
            self._try_transition_case_status(case, CaseStatus.ACTION_READY, "action ready for approval")

        elif self._is_waiting_for_external_reply(text_lower, commitments, evidence_still_needed):
            # Provider indicated they are investigating/reviewing internally and will follow up
            target_stage = WorkflowStage.AWAITING_RESPONSE
            target_wait_state = WorkflowWaitState.WAITING_FOR_EXTERNAL_RESPONSE
            target_pending_evidence = []
            target_commitments = commitments
            target_recommendation = (
                "Provider has taken the claim under internal review. Awaiting formal provider response."
            )
            target_action_id = None
            self._try_transition_case_status(case, CaseStatus.AWAITING_RESPONSE, "awaiting provider investigation")

        elif triggered_by_response and suggested_action_dict and self._is_concrete_action(suggested_action_dict):
            # Propose at most one concrete action in PENDING_APPROVAL status
            action_type_str = suggested_action_dict.get("action_type")
            action_type = ActionType(action_type_str)

            payload = suggested_action_dict.get("payload") or {}
            if action_type == ActionType.SEND_MESSAGE:
                payload["is_simulated"] = True

            new_action = Action(
                case_id=case_id,
                action_type=action_type,
                title=suggested_action_dict.get("title") or "Proposed Action",
                description=suggested_action_dict.get("description") or "Action proposed by orchestrator based on case analysis.",
                payload_json=payload,
                status=ActionStatus.PENDING_APPROVAL,
            )
            self.db.add(new_action)
            self.db.flush()

            # Record timeline event for proposed action
            self.db.add(
                CaseEvent(
                    case_id=case_id,
                    event_type=EventType.ACTION_CREATED,
                    description=f"Action proposed by orchestrator: '{new_action.title}' ({new_action.action_type.value}).",
                    source_type=EventSource.SYSTEM,
                    metadata_json={
                        "action_id": new_action.id,
                        "action_type": new_action.action_type.value,
                        "title": new_action.title,
                        "status": new_action.status.value,
                        "orchestrated": True,
                        "is_simulated": True,
                    },
                )
            )

            target_stage = WorkflowStage.ACTION_PENDING
            target_wait_state = WorkflowWaitState.WAITING_FOR_ACTION_APPROVAL
            target_action_id = new_action.id
            target_recommendation = f"Review and approve proposed action: '{new_action.title}'."
            target_pending_evidence = []
            target_commitments = commitments
            self._try_transition_case_status(case, CaseStatus.ACTION_READY, "orchestrator proposed action")

        elif any("replacement" in c.lower() for c in commitments):
            # Replacement authorization recorded: recommend user review resolution terms
            target_stage = WorkflowStage.UNDER_REVIEW
            target_wait_state = WorkflowWaitState.NONE
            target_pending_evidence = []
            target_commitments = commitments
            target_action_id = None
            target_recommendation = (
                "Provider has offered a replacement authorization. Review the available resolution "
                "terms and decide whether to draft an appropriate response to confirm replacement details."
            )
            self._try_transition_case_status(case, CaseStatus.UNDER_REVIEW, "provider replacement offered")

        elif any("refund" in c.lower() or "credit note" in c.lower() for c in commitments):
            # Commercial refund or credit note offered
            target_stage = WorkflowStage.UNDER_REVIEW
            target_wait_state = WorkflowWaitState.NONE
            target_pending_evidence = []
            target_commitments = commitments
            target_action_id = None
            target_recommendation = (
                "Provider has offered a refund or credit note. Review the settlement terms "
                "and decide whether to draft an appropriate response."
            )
            self._try_transition_case_status(case, CaseStatus.UNDER_REVIEW, "provider refund offered")

        elif commitments:
            # Other provider commitments recorded
            target_stage = WorkflowStage.UNDER_REVIEW
            target_wait_state = WorkflowWaitState.NONE
            target_pending_evidence = []
            target_commitments = commitments
            target_action_id = None
            target_recommendation = (
                f"Provider recorded commitment: '{commitments[0]}'. Review the available resolution "
                "terms and decide whether to draft an appropriate response."
            )
            self._try_transition_case_status(case, CaseStatus.UNDER_REVIEW, "provider commitment recorded")

        elif case.status == CaseStatus.AWAITING_RESPONSE:
            # Case is explicitly in AWAITING_RESPONSE status
            target_stage = WorkflowStage.AWAITING_RESPONSE
            target_wait_state = WorkflowWaitState.WAITING_FOR_EXTERNAL_RESPONSE
            target_pending_evidence = []
            target_commitments = commitments
            target_recommendation = (
                "Awaiting external provider response. Follow up if turnaround deadline elapses."
            )
            target_action_id = None

        elif case.status == CaseStatus.COLLECTING_EVIDENCE:
            target_stage = WorkflowStage.EVIDENCE_GATHERING
            target_wait_state = WorkflowWaitState.WAITING_FOR_USER_INPUT
            if "INVOICE" not in current_rep:
                target_pending_evidence = ["Original purchase invoice / proof of purchase"]
                target_recommendation = (
                    "Upload proof of purchase (invoice or receipt) to establish warranty eligibility and claim details."
                )
            else:
                target_pending_evidence = []
                target_recommendation = (
                    "All requested evidence has been provided. Upload optional supporting records if available, or proceed to case evaluation."
                )
            target_commitments = commitments
            target_action_id = None

        else:
            # Default state based on current case status
            if case.status == CaseStatus.NEW:
                target_stage = WorkflowStage.INTAKE
                target_wait_state = WorkflowWaitState.NONE
                target_recommendation = "Initial case evaluation required."
            else:
                target_stage = WorkflowStage.UNDER_REVIEW
                target_wait_state = WorkflowWaitState.NONE
                target_recommendation = recommended_step or "Case facts and evidence are under review."
            target_pending_evidence = evidence_still_needed
            target_commitments = commitments
            target_action_id = None
            if case.status in {CaseStatus.NEW} and (processing_result or triggered_by_response):
                self._try_transition_case_status(case, CaseStatus.UNDER_REVIEW, "case under review")

        # Apply state updates
        workflow_state.stage = target_stage
        workflow_state.wait_state = target_wait_state
        workflow_state.latest_recommendation = target_recommendation
        workflow_state.pending_evidence = target_pending_evidence
        workflow_state.outstanding_commitments = target_commitments
        workflow_state.active_action_id = target_action_id

        now = get_utc_now()
        workflow_state.last_reassessed_at = now
        workflow_state.updated_at = now

        # Record timeline event if workflow state materially changed
        has_material_change = (
            prev_stage != target_stage
            or prev_wait_state != target_wait_state
            or prev_action_id != target_action_id
            or prev_rec != target_recommendation
            or prev_pending != target_pending_evidence
        )

        if has_material_change and record_event:
            self.db.add(
                CaseEvent(
                    case_id=case_id,
                    event_type=EventType.WORKFLOW_REASSESSED,
                    description=(
                        f"Workflow reassessed: stage transitioned to {target_stage.value}, "
                        f"wait state is {target_wait_state.value}."
                    ),
                    source_type=EventSource.SYSTEM,
                    metadata_json={
                        "stage": target_stage.value,
                        "wait_state": target_wait_state.value,
                        "active_action_id": target_action_id,
                        "pending_evidence": target_pending_evidence,
                        "outstanding_commitments": target_commitments,
                        "latest_recommendation": target_recommendation,
                    },
                )
            )

        self.db.flush()
        return workflow_state

    def _is_waiting_for_external_reply(
        self,
        text_lower: str,
        commitments: List[str],
        evidence_still_needed: List[str],
    ) -> bool:
        """
        Detect if the provider response indicates internal handling where ResolveAI must wait.
        True when provider says claim is forwarded, under investigation, or in progress,
        and no user documents were requested and no final resolution offer (replacement/refund) was made.
        """
        if evidence_still_needed:
            return False

        has_resolution_offer = any(
            w in text_lower for w in ["agreed to replace", "replacement authorized", "refund will be issued", "credit note"]
        )
        if has_resolution_offer:
            return False

        internal_review_signals = [
            "under review",
            "forwarded to",
            "forwarded your claim",
            "engineering team",
            "technical team",
            "investigating",
            "investigation in progress",
            "will revert",
            "please await our",
            "please allow 3-5",
            "please allow 24-48",
            "ticket received and is being processed",
        ]
        return any(sig in text_lower for sig in internal_review_signals)

    def _is_concrete_action(self, suggested_action: Dict[str, Any]) -> bool:
        """Verify that a suggested action dictionary conforms to concrete action types."""
        if not isinstance(suggested_action, dict):
            return False
        action_type = suggested_action.get("action_type")
        return action_type in {ActionType.SEND_MESSAGE.value, ActionType.SCHEDULE_FOLLOW_UP.value}

    def _try_transition_case_status(self, case: Case, target_status: CaseStatus, reason: str) -> bool:
        """Attempt to update case status safely according to VALID_STATUS_TRANSITIONS."""
        if case.status == target_status:
            return False

        allowed_transitions = VALID_STATUS_TRANSITIONS.get(case.status, set())
        if target_status in allowed_transitions:
            old_status = case.status
            case.status = target_status
            case.updated_at = get_utc_now()
            self.db.add(
                CaseEvent(
                    case_id=case.id,
                    event_type=EventType.STATUS_CHANGED,
                    description=f"Status transitioned from {old_status.value} to {target_status.value} ({reason}).",
                    source_type=EventSource.SYSTEM,
                    metadata_json={
                        "previous_status": old_status.value,
                        "new_status": target_status.value,
                        "reason": reason,
                    },
                )
            )
            return True
        return False
