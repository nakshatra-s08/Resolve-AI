from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.policy import PolicySourceType


class PolicySourceRead(BaseModel):
    """Schema for listing policy sources (omits full document text)."""
    id: str
    title: str
    source_url: Optional[str] = None
    source_type: PolicySourceType
    jurisdiction: Optional[str] = None
    product_category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PolicySourceDetail(PolicySourceRead):
    """Schema for detailed policy view, including full document text."""
    document_text: str
    retrieved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicySearchRequest(BaseModel):
    """Request schema for searching policy library."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query terms")
    product_category: Optional[str] = Field(None, max_length=64, description="Optional product filter")
    jurisdiction: Optional[str] = Field(None, max_length=64, description="Optional jurisdiction filter")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of passages to return")


class PolicySearchResultItem(BaseModel):
    """Individual retrieved policy source passage."""
    source_id: str
    source_title: str
    source_url: Optional[str] = None
    source_type: PolicySourceType
    jurisdiction: Optional[str] = None
    product_category: Optional[str] = None
    passage: str
    relevance_score: float = Field(..., description="Lexical relevance score (not a probability)")


class PolicySearchResponse(BaseModel):
    """Response containing retrieved policy passages."""
    query: str
    total_results: int
    results: List[PolicySearchResultItem]
