from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.event import EventType, EventSource


class CaseEventCreate(BaseModel):
    """Schema for explicitly creating a user note on a case."""
    event_type: Literal[EventType.NOTE_ADDED] = Field(
        default=EventType.NOTE_ADDED,
        description="Must be NOTE_ADDED for explicit event creation.",
    )
    description: str = Field(
        ...,
        description="Human-readable description or note content.",
        min_length=1,
    )

    @field_validator("description")
    @classmethod
    def validate_not_whitespace(cls, value: str, info) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("description cannot be empty or whitespace only")
        return stripped

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "event_type": "NOTE_ADDED",
                "description": "Customer mentioned technician claimed the battery was replaced.",
            }
        },
    )


class CaseEventRead(BaseModel):
    """Schema for returning timeline event details."""
    id: str
    case_id: str
    event_type: EventType
    description: str
    source_type: EventSource
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "7b093d6e-98b6-4556-91e8-7824ea43940c",
                "case_id": "e3a89047-36e2-45e0-8bc2-a279144ce10e",
                "event_type": "STATUS_CHANGED",
                "description": "Status changed from NEW to UNDER_REVIEW",
                "source_type": "SYSTEM",
                "metadata_json": {
                    "previous_status": "NEW",
                    "new_status": "UNDER_REVIEW",
                },
                "created_at": "2026-10-12T10:05:00Z",
            }
        },
    )
