from datetime import datetime
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.models.action import ActionType, ActionStatus


class SendMessagePayload(BaseModel):
    """Payload definition for SEND_MESSAGE action."""
    recipient: str = Field(..., min_length=1, max_length=255, description="Destination description or email")
    subject: Optional[str] = Field(None, max_length=255, description="Message subject line")
    message_body: str = Field(..., min_length=1, description="Content of the proposed message")
    is_simulated: bool = Field(True, description="Explicit flag noting destination environment is simulated")

    @field_validator("recipient", "message_body")
    @classmethod
    def validate_not_whitespace(cls, value: str, info) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} cannot be empty or whitespace only")
        return stripped


class ScheduleFollowUpPayload(BaseModel):
    """Payload definition for SCHEDULE_FOLLOW_UP action."""
    due_at: datetime = Field(..., description="Target follow-up date and time in UTC")
    purpose: str = Field(..., min_length=1, max_length=500, description="Follow-up objective or expected response")

    @field_validator("purpose")
    @classmethod
    def validate_purpose_not_whitespace(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("purpose cannot be empty or whitespace only")
        return stripped


class ActionCreate(BaseModel):
    """Schema for creating a proposed action for a case."""
    action_type: ActionType
    title: str = Field(..., min_length=1, max_length=255, description="Short summary of action")
    description: str = Field(..., min_length=1, description="Context and justification for the action")
    payload: Dict[str, Any] = Field(..., description="Action-specific structured payload")

    @field_validator("title", "description")
    @classmethod
    def validate_strings(cls, value: str, info) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} cannot be empty or whitespace only")
        return stripped

    @model_validator(mode="after")
    def validate_payload_matches_type(self) -> "ActionCreate":
        if self.action_type == ActionType.SEND_MESSAGE:
            # Validate against SendMessagePayload schema
            parsed = SendMessagePayload.model_validate(self.payload)
            self.payload = parsed.model_dump(mode="json")
        elif self.action_type == ActionType.SCHEDULE_FOLLOW_UP:
            # Validate against ScheduleFollowUpPayload schema
            parsed = ScheduleFollowUpPayload.model_validate(self.payload)
            self.payload = parsed.model_dump(mode="json")
        return self


class ActionUpdate(BaseModel):
    """Schema for editing an existing DRAFT or PENDING_APPROVAL action."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    payload: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", "description")
    @classmethod
    def validate_optional_strings(cls, value: Optional[str], info) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError(f"{info.field_name} cannot be empty or whitespace only")
            return stripped
        return value


class ActionRead(BaseModel):
    """Public schema for an action record."""
    id: str
    case_id: str
    action_type: ActionType
    title: str
    description: str
    payload_json: Dict[str, Any]
    status: ActionStatus
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    execution_result_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActionExecutionResponse(BaseModel):
    """Response returned upon action execution."""
    action_id: str
    case_id: str
    action_type: ActionType
    status: ActionStatus
    executed_at: datetime
    is_simulated: bool
    execution_result: Dict[str, Any]
    message: str


class FollowUpItem(BaseModel):
    """Schema for follow-up record retrieval."""
    action_id: str
    case_id: str
    title: str
    due_at: datetime
    purpose: str
    status: ActionStatus
    is_overdue: bool
