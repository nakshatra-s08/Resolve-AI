from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.case import Case
from app.models.event import CaseEvent, EventType, EventSource
from app.schemas.analysis import (
    CaseAnalysisResponse,
    CaseChatRequest,
    CaseChatResponse,
)
from app.services.context import CaseContextService
from app.services.retrieval import PolicyRetrievalService
from app.services.ai_factory import get_ai_provider

router = APIRouter(prefix="/cases/{case_id}", tags=["Analysis & Reasoning"])


@router.post("/analysis", response_model=CaseAnalysisResponse)
def analyze_case(
    case_id: str,
    db: Session = Depends(get_db),
) -> CaseAnalysisResponse:
    """
    Generate a case-aware structured analysis and next-step recommendation.
    Retrieves case timeline, evidence text, and relevant policy passages.
    """
    context_service = CaseContextService(db)
    context = context_service.assemble_context(case_id)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    # Retrieve relevant policy passages using case context
    retrieval_service = PolicyRetrievalService(db)
    policies = retrieval_service.search(
        query=context["suggested_query"],
        product_category="laptop",
        limit=3,
    )

    # Invoke configured reasoning provider
    provider = get_ai_provider()
    analysis = provider.analyze_case(context, policies)

    # Record analysis event in case timeline without leaking prompts
    event = CaseEvent(
        case_id=case_id,
        event_type=EventType.SYSTEM_EVENT,
        description=f"Automated case analysis generated ({analysis.engine_mode} mode).",
        source_type=EventSource.SYSTEM,
        metadata_json={
            "engine_mode": analysis.engine_mode,
            "recommended_next_step": analysis.recommended_next_step,
            "policy_citations_count": len(policies),
        },
    )
    db.add(event)
    db.commit()

    return analysis


@router.post("/chat", response_model=CaseChatResponse)
def chat_with_case(
    case_id: str,
    req: CaseChatRequest,
    db: Session = Depends(get_db),
) -> CaseChatResponse:
    """
    Grounded case assistant endpoint.
    Answers user questions using case timeline, evidence, and policy sources.
    """
    message = req.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Chat message cannot be empty or whitespace only.",
        )

    context_service = CaseContextService(db)
    context = context_service.assemble_context(case_id)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    # Search policy passages matching the user's specific question
    retrieval_service = PolicyRetrievalService(db)
    policies = retrieval_service.search(
        query=message,
        product_category="laptop",
        limit=2,
    )

    provider = get_ai_provider()
    return provider.answer_case_question(context, policies, message)
