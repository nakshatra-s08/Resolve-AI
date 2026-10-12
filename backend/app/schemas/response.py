from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.response import ResponseProcessingStatus
from app.schemas.policy import PolicySearchResultItem


class SimulatedResponseCreate(BaseModel):
    """Schema for receiving a simulated provider response."""
    response_text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The content of the simulated service provider response.",
    )
    related_action_id: Optional[str] = Field(
        None,
        description="Optional ID of the action being answered.",
    )
    provider_name: Optional[str] = Field(
        "Simulated Service Provider",
        max_length=255,
        description="Display label for the simulated provider.",
    )

    @field_validator("response_text")
    @classmethod
    def validate_not_whitespace(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("response_text cannot be empty or whitespace only")
        return stripped


class SimulatedResponseRead(BaseModel):
    """Public representation of a stored simulated response."""
    id: str
    case_id: str
    related_action_id: Optional[str] = None
    provider_name: str
    response_text: str
    source_type: Literal["SIMULATION"]
    status: ResponseProcessingStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    is_simulated: bool = Field(True, description="Always true, clearly noting simulated origin")

    model_config = ConfigDict(from_attributes=True)


class ResponseProcessingResult(BaseModel):
    """Structured analytical findings produced from processing a simulated provider response."""
    case_id: str
    response_id: str
    engine_mode: Literal["demo", "live"]
    summary: str
    requested_information: List[str] = Field(
        default_factory=list,
        description="Specific documents, dates, or details requested by the provider",
    )
    identified_commitments: List[str] = Field(
        default_factory=list,
        description="Explicit commitments, deadlines, or offers made in the response",
    )
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Ambiguous or non-committal statements requiring clarification",
    )
    evidence_already_available: List[str] = Field(
        default_factory=list,
        description="Requested items that already exist in case evidence",
    )
    evidence_still_needed: List[str] = Field(
        default_factory=list,
        description="Items requested that are still missing from case evidence",
    )
    recommended_next_step: str
    supporting_policy_sources: List[PolicySearchResultItem] = Field(default_factory=list)
    uncertainty_notes: List[str] = Field(default_factory=list)
    suggested_action: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional proposed action definition ready for review",
    )
    suggested_case_status: Optional[str] = Field(
        None,
        description="Recommended next status transition for the case (e.g. COLLECTING_EVIDENCE or UNDER_REVIEW)",
    )
    processed_at: datetime
