from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.policy import PolicySource
from app.schemas.policy import (
    PolicySourceRead,
    PolicySourceDetail,
    PolicySearchRequest,
    PolicySearchResponse,
)
from app.services.retrieval import PolicyRetrievalService

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("", response_model=List[PolicySourceRead])
def list_policies(db: Session = Depends(get_db)) -> List[PolicySource]:
    """List available policy documents without full document text."""
    return db.query(PolicySource).order_by(PolicySource.id.asc()).all()


@router.get("/{policy_id}", response_model=PolicySourceDetail)
def get_policy_detail(policy_id: str, db: Session = Depends(get_db)) -> PolicySource:
    """Retrieve complete policy source document details."""
    policy = db.query(PolicySource).filter(PolicySource.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy source with ID '{policy_id}' was not found.",
        )
    return policy


@router.post("/search", response_model=PolicySearchResponse)
def search_policies(
    req: PolicySearchRequest,
    db: Session = Depends(get_db),
) -> PolicySearchResponse:
    """Search policy library for relevant passages."""
    service = PolicyRetrievalService(db)
    results = service.search(
        query=req.query,
        product_category=req.product_category,
        jurisdiction=req.jurisdiction,
        limit=req.limit,
    )
    return PolicySearchResponse(
        query=req.query,
        total_results=len(results),
        results=results,
    )
