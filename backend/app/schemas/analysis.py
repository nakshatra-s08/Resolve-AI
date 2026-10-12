from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.models.case import CaseStatus
from app.models.evidence import EvidenceType
from app.schemas.policy import PolicySearchResultItem


class AnalysisKnownFact(BaseModel):
    category: str = Field(..., description="E.g., USER_REPORTED, EXTRACTED_FROM_DOCUMENT, POLICY_STANDARD")
    fact: str


class AnalysisMissingInfo(BaseModel):
    item: str
    impact: str


class CaseAnalysisResponse(BaseModel):
    """Structured case-aware analysis and recommendation schema."""
    case_id: str
    engine_mode: Literal["demo", "live"]
    summary: str
    recommended_next_step: str
    reasoning: str
    known_facts: List[AnalysisKnownFact]
    missing_information: List[AnalysisMissingInfo]
    evidence_considered: List[str]
    supporting_policy_sources: List[PolicySearchResultItem]
    uncertainty_notes: List[str]
    suggested_action: Optional[str] = None
    generated_at: datetime


class CaseChatRequest(BaseModel):
    """Request schema for asking a case-specific question."""
    message: str = Field(..., min_length=1, max_length=2000, description="User question or statement")


class CaseChatResponse(BaseModel):
    """Response schema for case chat."""
    case_id: str
    engine_mode: Literal["demo", "live"]
    question: str
    answer: str
    distinction_notes: List[str] = Field(
        default_factory=list,
        description="Distinction between user facts, extracted facts, policy, and inferences",
    )
    supporting_policy_sources: List[PolicySearchResultItem]
    generated_at: datetime
