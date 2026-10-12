from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.case import Case, CaseStatus
from app.models.action import Action, ActionType, ActionStatus, get_utc_now
from app.models.event import CaseEvent, EventType, EventSource
from app.schemas.action import (
    ActionCreate,
    ActionUpdate,
    ActionRead,
    ActionExecutionResponse,
    FollowUpItem,
    SendMessagePayload,
    ScheduleFollowUpPayload,
)
from app.services.action_executor import SimulatedActionService

router = APIRouter(tags=["Actions & Follow-ups"])


# ==========================================
# CASE-SCOPED ACTION ENDPOINTS
# ==========================================

@router.post(
    "/cases/{case_id}/actions",
    response_model=ActionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_action(
    case_id: str,
    action_in: ActionCreate,
    db: Session = Depends(get_db),
) -> Action:
    """Propose a new action for a case. Requires explicit user approval before execution."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    db_action = Action(
        case_id=case_id,
        action_type=action_in.action_type,
        title=action_in.title,
        description=action_in.description,
        payload_json=action_in.payload,
        status=ActionStatus.PENDING_APPROVAL,
    )
    db.add(db_action)
    db.flush()

    # Record event in timeline without leaking sensitive raw bodies
    event = CaseEvent(
        case_id=case_id,
        event_type=EventType.ACTION_CREATED,
        description=f"Action proposed: '{db_action.title}' ({db_action.action_type.value}).",
        source_type=EventSource.SYSTEM,
        metadata_json={
            "action_id": db_action.id,
            "action_type": db_action.action_type.value,
            "title": db_action.title,
            "status": db_action.status.value,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(db_action)
    return db_action


@router.get("/cases/{case_id}/actions", response_model=List[ActionRead])
def list_case_actions(
    case_id: str,
    db: Session = Depends(get_db),
) -> List[Action]:
    """List all actions proposed, approved, or executed for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    return (
        db.query(Action)
        .filter(Action.case_id == case_id)
        .order_by(Action.created_at.desc())
        .all()
    )


@router.get("/cases/{case_id}/follow-ups", response_model=List[FollowUpItem])
def list_case_follow_ups(
    case_id: str,
    db: Session = Depends(get_db),
) -> List[FollowUpItem]:
    """Retrieve scheduled follow-ups for a case, computing real-time overdue status."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    actions = (
        db.query(Action)
        .filter(
            Action.case_id == case_id,
            Action.action_type == ActionType.SCHEDULE_FOLLOW_UP,
        )
        .order_by(Action.created_at.desc())
        .all()
    )

    now = get_utc_now()
    results = []
    for act in actions:
        payload = act.payload_json or {}
        raw_due = payload.get("due_at")
        purpose = payload.get("purpose", "")

        due_dt = None
        if isinstance(raw_due, str):
            try:
                due_dt = datetime.fromisoformat(raw_due)
            except Exception:
                due_dt = now
        elif isinstance(raw_due, datetime):
            due_dt = raw_due
        else:
            due_dt = now

        # Ensure due_dt is timezone-aware for comparison
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)

        is_overdue = now > due_dt and act.status != ActionStatus.CANCELLED

        results.append(
            FollowUpItem(
                action_id=act.id,
                case_id=act.case_id,
                title=act.title,
                due_at=due_dt,
                purpose=purpose,
                status=act.status,
                is_overdue=is_overdue,
            )
        )

    return results


# ==========================================
# ACTION-SCOPED DIRECT ENDPOINTS
# ==========================================

@router.get("/actions/{action_id}", response_model=ActionRead)
def get_action_detail(
    action_id: str,
    db: Session = Depends(get_db),
) -> Action:
    """Retrieve a single action by ID."""
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action with ID '{action_id}' was not found.",
        )
    return action


@router.patch("/actions/{action_id}", response_model=ActionRead)
def edit_action(
    action_id: str,
    action_update: ActionUpdate,
    db: Session = Depends(get_db),
) -> Action:
    """
    Edit permitted fields of an action while in DRAFT or PENDING_APPROVAL.
    Modifying an action invalidates any prior approval, requiring re-approval.
    """
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action with ID '{action_id}' was not found.",
        )

    if action.status in {ActionStatus.EXECUTED, ActionStatus.REJECTED, ActionStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit an action with status '{action.status.value}'.",
        )

    update_data = action_update.model_dump(exclude_unset=True)
    if not update_data:
        return action

    # Validate payload against action type if payload is being updated
    if "payload" in update_data and update_data["payload"] is not None:
        if action.action_type == ActionType.SEND_MESSAGE:
            parsed = SendMessagePayload.model_validate(update_data["payload"])
            update_data["payload_json"] = parsed.model_dump(mode="json")
        elif action.action_type == ActionType.SCHEDULE_FOLLOW_UP:
            parsed = ScheduleFollowUpPayload.model_validate(update_data["payload"])
            update_data["payload_json"] = parsed.model_dump(mode="json")
        del update_data["payload"]

    for field, val in update_data.items():
        setattr(action, field, val)

    # Invalidate previous approval and revert to PENDING_APPROVAL
    action.status = ActionStatus.PENDING_APPROVAL
    action.approved_at = None
    action.updated_at = get_utc_now()

    event = CaseEvent(
        case_id=action.case_id,
        event_type=EventType.ACTION_UPDATED,
        description=f"Action edited: '{action.title}'. Re-approval is required.",
        source_type=EventSource.USER,
        metadata_json={
            "action_id": action.id,
            "status": action.status.value,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(action)
    return action


@router.post("/actions/{action_id}/approve", response_model=ActionRead)
def approve_action(
    action_id: str,
    db: Session = Depends(get_db),
) -> Action:
    """Explicit user approval for a pending action."""
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action with ID '{action_id}' was not found.",
        )

    if action.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve action with status '{action.status.value}'. Must be PENDING_APPROVAL.",
        )

    now = get_utc_now()
    action.status = ActionStatus.APPROVED
    action.approved_at = now
    action.updated_at = now

    event = CaseEvent(
        case_id=action.case_id,
        event_type=EventType.ACTION_APPROVED,
        description=f"Action approved: '{action.title}'. Ready for simulated execution.",
        source_type=EventSource.USER,
        metadata_json={
            "action_id": action.id,
            "approved_at": now.isoformat(),
        },
    )
    db.add(event)
    db.commit()
    db.refresh(action)
    return action


@router.post("/actions/{action_id}/reject", response_model=ActionRead)
def reject_action(
    action_id: str,
    db: Session = Depends(get_db),
) -> Action:
    """Explicit user rejection of an action, preventing its execution."""
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action with ID '{action_id}' was not found.",
        )

    if action.status not in {ActionStatus.PENDING_APPROVAL, ActionStatus.APPROVED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject action with status '{action.status.value}'.",
        )

    now = get_utc_now()
    action.status = ActionStatus.REJECTED
    action.updated_at = now

    event = CaseEvent(
        case_id=action.case_id,
        event_type=EventType.ACTION_REJECTED,
        description=f"Action rejected: '{action.title}'. Execution prevented.",
        source_type=EventSource.USER,
        metadata_json={
            "action_id": action.id,
            "status": ActionStatus.REJECTED.value,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(action)
    return action


@router.post("/actions/{action_id}/execute", response_model=ActionExecutionResponse)
def execute_action(
    action_id: str,
    db: Session = Depends(get_db),
) -> ActionExecutionResponse:
    """
    Execute an approved action within a safe simulated environment.
    Strictly verifies approval state before execution. Idempotent on repeated calls.
    """
    action = db.query(Action).filter(Action.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action with ID '{action_id}' was not found.",
        )

    # Idempotency check: If already executed, return existing result without re-executing
    if action.status == ActionStatus.EXECUTED:
        return ActionExecutionResponse(
            action_id=action.id,
            case_id=action.case_id,
            action_type=action.action_type,
            status=action.status,
            executed_at=action.executed_at or get_utc_now(),
            is_simulated=True,
            execution_result=action.execution_result_json or {},
            message="Action was already executed previously (idempotent response).",
        )

    # Strict approval verification
    if action.status != ActionStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Action execution blocked. Current status is '{action.status.value}'. "
                "Actions must be explicitly APPROVED before execution."
            ),
        )

    executor = SimulatedActionService()
    new_status, result_payload, message_text = executor.execute_action(action)

    now = get_utc_now()
    action.status = new_status
    action.executed_at = now
    action.updated_at = now
    action.execution_result_json = result_payload

    # Record execution event in timeline
    event = CaseEvent(
        case_id=action.case_id,
        event_type=EventType.ACTION_EXECUTED if new_status == ActionStatus.EXECUTED else EventType.ACTION_FAILED,
        description=f"Action executed (simulated): '{action.title}'.",
        source_type=EventSource.SIMULATION,
        metadata_json={
            "action_id": action.id,
            "action_type": action.action_type.value,
            "status": new_status.value,
            "simulated": True,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(action)

    return ActionExecutionResponse(
        action_id=action.id,
        case_id=action.case_id,
        action_type=action.action_type,
        status=action.status,
        executed_at=action.executed_at,
        is_simulated=True,
        execution_result=action.execution_result_json,
        message=message_text,
    )
