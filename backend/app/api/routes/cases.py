from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.case import Case, CaseStatus, VALID_STATUS_TRANSITIONS, get_utc_now
from app.models.event import CaseEvent, EventType, EventSource
from app.schemas.case import CaseCreate, CaseUpdate, CaseStatusUpdate, CaseRead
from app.schemas.event import CaseEventCreate, CaseEventRead

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(case_in: CaseCreate, db: Session = Depends(get_db)) -> Case:
    """Create a new repair case and automatically record the initial CASE_CREATED event."""
    db_case = Case(
        title=case_in.title,
        product_name=case_in.product_name,
        issue_description=case_in.issue_description,
        status=CaseStatus.NEW,
    )
    db.add(db_case)
    db.flush()  # Ensures db_case.id is generated for the foreign key

    event = CaseEvent(
        case_id=db_case.id,
        event_type=EventType.CASE_CREATED,
        description=f"Case created for product '{db_case.product_name}' with initial status NEW.",
        source_type=EventSource.SYSTEM,
        metadata_json={
            "initial_status": CaseStatus.NEW.value,
            "product_name": db_case.product_name,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(db_case)
    return db_case


@router.get("", response_model=List[CaseRead])
def list_cases(db: Session = Depends(get_db)) -> List[Case]:
    """List all repair cases ordered by creation timestamp descending."""
    return db.query(Case).order_by(Case.created_at.desc()).all()


@router.get("/{case_id}", response_model=CaseRead)
def get_case(case_id: str, db: Session = Depends(get_db)) -> Case:
    """Retrieve a single repair case by ID."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )
    return db_case


@router.patch("/{case_id}", response_model=CaseRead)
def update_case(
    case_id: str,
    case_update: CaseUpdate,
    db: Session = Depends(get_db),
) -> Case:
    """Partially update case editable fields (title, product_name, issue_description)."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    update_data = case_update.model_dump(exclude_unset=True)
    if not update_data:
        return db_case

    changed_fields = []
    old_values = {}
    new_values = {}

    for field, new_val in update_data.items():
        old_val = getattr(db_case, field)
        if old_val != new_val:
            setattr(db_case, field, new_val)
            changed_fields.append(field)
            old_values[field] = old_val
            new_values[field] = new_val

    if changed_fields:
        db_case.updated_at = get_utc_now()
        event = CaseEvent(
            case_id=db_case.id,
            event_type=EventType.CASE_UPDATED,
            description=f"Case updated: modified {', '.join(changed_fields)}.",
            source_type=EventSource.SYSTEM,
            metadata_json={
                "changed_fields": changed_fields,
                "old_values": old_values,
                "new_values": new_values,
            },
        )
        db.add(event)
        db.commit()
        db.refresh(db_case)

    return db_case


@router.patch("/{case_id}/status", response_model=CaseRead)
def update_case_status(
    case_id: str,
    status_update: CaseStatusUpdate,
    db: Session = Depends(get_db),
) -> Case:
    """Transition a case's workflow status according to state machine rules."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    current_status = db_case.status
    target_status = status_update.status

    # If status is identical, do nothing (avoid duplicate events)
    if current_status == target_status:
        return db_case

    allowed_targets = VALID_STATUS_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_targets:
        allowed_names = ", ".join(s.value for s in allowed_targets) or "None"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Invalid status transition from '{current_status.value}' to '{target_status.value}'. "
                f"Allowed target statuses: [{allowed_names}]."
            ),
        )

    db_case.status = target_status
    db_case.updated_at = get_utc_now()

    event = CaseEvent(
        case_id=db_case.id,
        event_type=EventType.STATUS_CHANGED,
        description=f"Status changed from {current_status.value} to {target_status.value}.",
        source_type=EventSource.SYSTEM,
        metadata_json={
            "previous_status": current_status.value,
            "new_status": target_status.value,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(db_case)
    return db_case


@router.post(
    "/{case_id}/events",
    response_model=CaseEventRead,
    status_code=status.HTTP_201_CREATED,
)
def add_case_note(
    case_id: str,
    event_in: CaseEventCreate,
    db: Session = Depends(get_db),
) -> CaseEvent:
    """Add a manual user note to a case's timeline."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    event = CaseEvent(
        case_id=db_case.id,
        event_type=EventType.NOTE_ADDED,
        description=event_in.description,
        source_type=EventSource.USER,
        metadata_json=None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{case_id}/timeline", response_model=List[CaseEventRead])
def get_case_timeline(
    case_id: str,
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max number of events to return"),
    db: Session = Depends(get_db),
) -> List[CaseEvent]:
    """Retrieve chronological timeline events for a case."""
    db_case = db.query(Case).filter(Case.id == case_id).first()
    if not db_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    events = (
        db.query(CaseEvent)
        .filter(CaseEvent.case_id == case_id)
        .order_by(CaseEvent.created_at.asc(), CaseEvent.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return events
