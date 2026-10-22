from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.workflow import WorkflowStage, WorkflowWaitState
from app.schemas.action import ActionRead


class WorkflowStateRead(BaseModel):
    """Schema representing the current agentic workflow state of a case."""
    id: str
    case_id: str
    goal: str
    stage: WorkflowStage
    wait_state: WorkflowWaitState
    latest_recommendation: Optional[str] = None
    pending_evidence: List[str] = Field(
        default_factory=list,
        description="List of document categories or details still required from the user",
    )
    outstanding_commitments: List[str] = Field(
        default_factory=list,
        description="Formal provider commitments or deadlines pending resolution",
    )
    active_action_id: Optional[str] = Field(
        None,
        description="ID of the concrete action awaiting approval or execution",
    )
    active_action: Optional[ActionRead] = Field(
        None,
        description="Full active action details if active_action_id is set",
    )
    last_reassessed_at: datetime
    updated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowStateUpdate(BaseModel):
    """Schema for updating workflow state manually if needed."""
    goal: Optional[str] = None
    stage: Optional[WorkflowStage] = None
    wait_state: Optional[WorkflowWaitState] = None
    latest_recommendation: Optional[str] = None
    pending_evidence: Optional[List[str]] = None
    outstanding_commitments: Optional[List[str]] = None
    active_action_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")
