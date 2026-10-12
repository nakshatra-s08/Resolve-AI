from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.case import Case, CaseStatus, VALID_STATUS_TRANSITIONS, get_utc_now
from app.models.action import Action, ActionType, ActionStatus
from app.models.event import CaseEvent, EventType, EventSource
from app.models.response import SimulatedResponse, ResponseProcessingStatus
from app.schemas.response import (
    SimulatedResponseCreate,
    SimulatedResponseRead,
    ResponseProcessingResult,
)
from app.services.context import CaseContextService
from app.services.retrieval import PolicyRetrievalService
from app.services.response_processor import ResponseProcessingService

router = APIRouter(prefix="/cases/{case_id}", tags=["Simulated Responses"])


@router.post(
    "/simulate-response",
    response_model=SimulatedResponseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_simulated_response(
    case_id: str,
    resp_in: SimulatedResponseCreate,
    db: Session = Depends(get_db),
) -> SimulatedResponse:
    """
    Ingest a simulated service provider response for a case.
    Validates related action and records an immutable timeline event.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    # Validate related action if provided
    related_action = None
    if resp_in.related_action_id:
        related_action = db.query(Action).filter(Action.id == resp_in.related_action_id).first()
        if not related_action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Related action with ID '{resp_in.related_action_id}' was not found.",
            )
        if related_action.case_id != case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Related action '{resp_in.related_action_id}' belongs to a different case, "
                    f"not case '{case_id}'."
                ),
            )

    provider_name = resp_in.provider_name or "Simulated Service Provider"

    db_response = SimulatedResponse(
        case_id=case_id,
        related_action_id=resp_in.related_action_id,
        provider_name=provider_name,
        response_text=resp_in.response_text,
        source_type="SIMULATION",
        status=ResponseProcessingStatus.RECEIVED,
    )
    db.add(db_response)
    db.flush()

    # Record event in timeline
    event = CaseEvent(
        case_id=case_id,
        event_type=EventType.SIMULATED_RESPONSE_RECEIVED,
        description=f"Simulated response received from '{provider_name}'.",
        source_type=EventSource.SIMULATION,
        metadata_json={
            "response_id": db_response.id,
            "provider_name": provider_name,
            "related_action_id": resp_in.related_action_id,
            "is_simulated": True,
        },
    )
    db.add(event)

    # If the case was AWAITING_RESPONSE, move it into UNDER_REVIEW via valid transition
    if case.status == CaseStatus.AWAITING_RESPONSE:
        case.status = CaseStatus.UNDER_REVIEW
        case.updated_at = get_utc_now()
        status_event = CaseEvent(
            case_id=case_id,
            event_type=EventType.STATUS_CHANGED,
            description="Status changed from AWAITING_RESPONSE to UNDER_REVIEW upon receiving provider response.",
            source_type=EventSource.SYSTEM,
            metadata_json={
                "previous_status": CaseStatus.AWAITING_RESPONSE.value,
                "new_status": CaseStatus.UNDER_REVIEW.value,
                "triggered_by_response_id": db_response.id,
            },
        )
        db.add(status_event)

    # If a related SCHEDULE_FOLLOW_UP action was associated, mark it EXECUTED/COMPLETED
    if related_action and related_action.action_type == ActionType.SCHEDULE_FOLLOW_UP:
        if related_action.status in {ActionStatus.PENDING_APPROVAL, ActionStatus.APPROVED}:
            related_action.status = ActionStatus.EXECUTED
            related_action.executed_at = get_utc_now()
            related_action.execution_result_json = {
                "completed_by_response_id": db_response.id,
                "simulated": True,
            }

    db.commit()
    db.refresh(db_response)
    return db_response


@router.get(
    "/responses",
    response_model=List[SimulatedResponseRead],
)
def list_simulated_responses(
    case_id: str,
    db: Session = Depends(get_db),
) -> List[SimulatedResponse]:
    """List all simulated responses received for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    return (
        db.query(SimulatedResponse)
        .filter(SimulatedResponse.case_id == case_id)
        .order_by(SimulatedResponse.created_at.desc())
        .all()
    )


@router.post(
    "/responses/{response_id}/process",
    response_model=ResponseProcessingResult,
)
def process_simulated_response(
    case_id: str,
    response_id: str,
    db: Session = Depends(get_db),
) -> ResponseProcessingResult:
    """
    Process a simulated response against current case context and policy library.
    Idempotent: repeating call on processed response returns cached findings without duplicate events.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    response = (
        db.query(SimulatedResponse)
        .filter(SimulatedResponse.id == response_id, SimulatedResponse.case_id == case_id)
        .first()
    )
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Response with ID '{response_id}' was not found for this case.",
        )

    # Idempotency check: If already processed, return stored result directly
    if response.status == ResponseProcessingStatus.PROCESSED and response.processing_result_json:
        return ResponseProcessingResult.model_validate(response.processing_result_json)

    # 1. Gather rich case context
    context_service = CaseContextService(db)
    context = context_service.assemble_context(case_id) or {}

    # 2. Retrieve relevant policy passages
    retrieval_service = PolicyRetrievalService(db)
    query = f"{context.get('product_name', 'Laptop')} {response.response_text[:200]}"
    policies = retrieval_service.search(query=query, product_category="laptop", limit=2)

    # 3. Analyze response
    processor = ResponseProcessingService(db)
    result = processor.process_response(case, response, context, policies)

    # 4. Update case status if recommended and valid
    if result.suggested_case_status:
        target_status = CaseStatus(result.suggested_case_status)
        if target_status in VALID_STATUS_TRANSITIONS.get(case.status, set()):
            old_status = case.status
            case.status = target_status
            case.updated_at = get_utc_now()
            db.add(
                CaseEvent(
                    case_id=case_id,
                    event_type=EventType.STATUS_CHANGED,
                    description=f"Status transitioned from {old_status.value} to {target_status.value} following response analysis.",
                    source_type=EventSource.SYSTEM,
                    metadata_json={
                        "previous_status": old_status.value,
                        "new_status": target_status.value,
                        "response_id": response.id,
                    },
                )
            )

    # 5. Persist processing result and update status
    now = get_utc_now()
    response.status = ResponseProcessingStatus.PROCESSED
    response.processed_at = now
    response.processing_result_json = result.model_dump(mode="json")

    # Record event in timeline
    event = CaseEvent(
        case_id=case_id,
        event_type=EventType.RESPONSE_PROCESSED,
        description=f"Simulated response processed: {result.summary}",
        source_type=EventSource.SYSTEM,
        metadata_json={
            "response_id": response.id,
            "engine_mode": result.engine_mode,
            "still_needed": result.evidence_still_needed,
            "commitments": result.identified_commitments,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(response)

    return result
