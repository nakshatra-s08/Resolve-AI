from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.case import Case, CaseStatus
from app.schemas.case import CaseCreate, CaseRead

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(case_in: CaseCreate, db: Session = Depends(get_db)) -> Case:
    """Create a new repair case."""
    db_case = Case(
        title=case_in.title,
        product_name=case_in.product_name,
        issue_description=case_in.issue_description,
        status=CaseStatus.NEW,
    )
    db.add(db_case)
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
